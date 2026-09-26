import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, build_opener, ProxyHandler

from .config import LauncherConfig


OLLAMA_READY_ATTEMPTS = 15
OLLAMA_READY_INTERVAL_SECONDS = 2


@dataclass(frozen=True)
class CoreStatus:
    core: str = 'Stopped'
    worker: str = 'Stopped'
    ollama: str = 'Unknown'
    relay: str = 'Unknown'
    detail: str = ''


def repository_root():
    return Path(__file__).resolve().parent.parent


def python_path(root=None):
    root = repository_root() if root is None else Path(root)
    return root / '.venv' / 'Scripts' / 'python.exe'


def probe_ollama(config, opener=None):
    opener = opener or build_opener(ProxyHandler({}))
    try:
        with opener.open(Request(config.ollama_url + '/api/tags'), timeout=3) as response:
            models = json.load(response).get('models', [])
        installed = any(item.get('name') == 'llama3.2:latest'
                        and item.get('digest') == config.model_digest for item in models)
        if not installed:
            return 'Available; required model or digest missing'
        with opener.open(Request(config.ollama_url + '/api/ps'), timeout=3) as response:
            running = json.load(response).get('models', [])
        loaded = any(item.get('name') in ('llama3.2', 'llama3.2:latest') for item in running)
        return 'Available; llama3.2 loaded' if loaded else 'Available; llama3.2 unloaded'
    except Exception:
        return 'Unavailable'


def start_ollama_application(env=None, popen=subprocess.Popen):
    env = os.environ if env is None else env
    local_app_data = env.get('LOCALAPPDATA')
    if not local_app_data:
        raise ValueError('Ollama application is unavailable')
    executable = Path(local_app_data) / 'Programs' / 'Ollama' / 'ollama app.exe'
    if not executable.is_file():
        raise ValueError('Ollama application is unavailable')
    flags = (getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
             | getattr(subprocess, 'DETACHED_PROCESS', 0))
    popen([str(executable)], cwd=str(executable.parent), stdin=subprocess.DEVNULL,
          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)


def wait_for_ollama(config, starter=start_ollama_application, probe=probe_ollama,
                    attempts=OLLAMA_READY_ATTEMPTS,
                    interval=OLLAMA_READY_INTERVAL_SECONDS, sleep=time.sleep):
    status = probe(config)
    if status != 'Unavailable':
        return status
    starter()
    for _ in range(attempts):
        sleep(interval)
        status = probe(config)
        if status != 'Unavailable':
            return status
    return 'Unavailable'


class CoreController:
    def __init__(self, config_loader=LauncherConfig.load, secret_store=None,
                 root=None, popen=subprocess.Popen, callback=None, poll_seconds=10,
                 ollama_starter=None, readiness_attempts=OLLAMA_READY_ATTEMPTS,
                 readiness_interval=OLLAMA_READY_INTERVAL_SECONDS,
                 readiness_sleep=time.sleep):
        self.config_loader = config_loader
        self.secret_store = secret_store
        self.root = repository_root() if root is None else Path(root)
        self.popen = popen
        self.callback = callback or (lambda status: None)
        self.poll_seconds = poll_seconds
        self.ollama_starter = ollama_starter
        self.readiness_attempts = readiness_attempts
        self.readiness_interval = readiness_interval
        self.readiness_sleep = readiness_sleep
        self.process = None
        self.status = CoreStatus()
        self._closing = threading.Event()
        self._monitor = None
        self._lock = threading.RLock()

    def _publish(self, **changes):
        values = self.status.__dict__.copy()
        values.update(changes)
        self.status = CoreStatus(**values)
        self.callback(self.status)

    @staticmethod
    def _stop_owned_process(process):
        if process.poll() is not None:
            return
        try:
            if process.stdin:
                process.stdin.write('STOP\n')
                process.stdin.flush()
            # Normal worker long-polling is bounded near ten seconds. Allow it
            # to observe STOP and run its cleanup before termination fallback.
            process.wait(timeout=15)
        except Exception:
            process.terminate()
            try:
                process.wait(timeout=3)
            except Exception:
                process.kill()

    def start(self):
        with self._lock:
            if self.process is not None and self.process.poll() is None:
                return False
            self._publish(core='Starting', worker='Starting', relay='Connecting', detail='')
            try:
                config = self.config_loader()
                secret = self.secret_store.read() if self.secret_store else None
                executable = python_path(self.root)
                if not executable.is_file():
                    raise ValueError('Expected Python environment is missing')
                ollama = wait_for_ollama(
                    config,
                    starter=self.ollama_starter or start_ollama_application,
                    probe=probe_ollama,
                    attempts=self.readiness_attempts,
                    interval=self.readiness_interval,
                    sleep=self.readiness_sleep)
                if ollama == 'Unavailable':
                    raise ValueError('Ollama did not become ready within the startup window')
                if 'missing' in ollama:
                    raise ValueError('Required Ollama model or digest is unavailable')
                env = os.environ.copy()
                env.update(config.worker_environment(secret))
                flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                self.process = self.popen([str(executable), '-m', 'worker'], cwd=str(self.root),
                                          env=env, stdin=subprocess.PIPE,
                                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                          text=True, creationflags=flags)
                self._publish(core='Online', worker='Running', ollama=ollama,
                              relay='Connecting')
                self._monitor = threading.Thread(target=self._watch, daemon=True,
                                                 name='oes-core-monitor')
                self._monitor.start()
                return True
            except Exception as error:
                process = self.process
                if process is not None:
                    self._stop_owned_process(process)
                self.process = None
                self._publish(core='Needs Attention', worker='Stopped', relay='Unknown',
                              detail=str(error))
                return False

    def _watch(self):
        process = self.process
        reader = threading.Thread(target=self._read_status, args=(process,), daemon=True,
                                  name='oes-core-status-reader')
        reader.start()
        while process.poll() is None and not self._closing.wait(self.poll_seconds):
            try:
                config = self.config_loader()
                self._publish(ollama=probe_ollama(config))
            except Exception:
                self._publish(ollama='Unknown')
        code = process.poll()
        if self.process is process:
            self.process = None
            if not self._closing.is_set() and code is not None:
                self._publish(core='Needs Attention', worker='Exited',
                              relay='Disconnected', detail='Worker exited unexpectedly')

    def _read_status(self, process):
        if process.stderr is None:
            return
        for line in process.stderr:
            # Parse only fixed content-free worker diagnostics. Raw output is discarded.
            if 'worker relay connected' in line:
                self._publish(relay='Connected')
            elif 'worker connection reset category=' in line:
                self._publish(relay='Reconnecting')

    def stop(self):
        with self._lock:
            process = self.process
            if process is None or process.poll() is not None:
                self.process = None
                self._publish(core='Stopped', worker='Stopped', relay='Disconnected')
                return
            self._publish(core='Stopping', worker='Stopping')
            self._stop_owned_process(process)
            self.process = None
            self._publish(core='Stopped', worker='Stopped', relay='Disconnected', detail='')

    def restart(self):
        self.stop()
        return self.start()

    def close(self):
        self._closing.set()
        self.stop()
