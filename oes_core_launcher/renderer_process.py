"""Owned process boundary for the native Eyeball and its visual tuner."""
import json
import subprocess
import sys
from pathlib import Path


RENDERER_RELATIVE_PATH = Path('build/oes-core-renderer/Release/oes-eyeball-renderer.exe')
RENDERER_BUILD_COMMAND = (
    'cmake -S oes_core_renderer -B build/oes-core-renderer -A x64\n'
    'cmake --build build/oes-core-renderer --config Release'
)


def renderer_executable(root):
    """Resolve only the renderer built from this repository checkout."""
    return Path(root).resolve() / RENDERER_RELATIVE_PATH


class NativeRendererProcess:
    def __init__(self, executable, diagnostics, popen=subprocess.Popen):
        self.executable = Path(executable)
        self.diagnostics = Path(diagnostics)
        self.popen = popen
        self.process = None

    def start(self):
        if self.process is not None and self.process.poll() is None:
            return False
        self.process = None
        if not self.executable.is_file():
            self._record_failure('renderer_executable_missing')
            return False
        try:
            self.process = self.popen(
                [str(self.executable), '--diagnostics', str(self.diagnostics)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            self.process = None
            self._record_failure('renderer_process_unavailable')
            return False
        return True

    def _record_failure(self, reason):
        try:
            self.diagnostics.parent.mkdir(parents=True, exist_ok=True)
            self.diagnostics.write_text(
                json.dumps({'status': 'failed', 'reason': reason}) + '\n',
                encoding='utf-8',
            )
        except OSError:
            pass

    def status(self):
        if not self.diagnostics.is_file():
            return None
        try:
            value = json.loads(self.diagnostics.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError, TypeError):
            return None
        return value if isinstance(value, dict) else None

    def close(self):
        process, self.process = self.process, None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()


class NativeEyeballManager:
    """Own at most one renderer and one tuner launched by OES Core."""

    def __init__(self, root, diagnostics, popen=subprocess.Popen, python=None):
        self.root = Path(root).resolve()
        self.popen = popen
        self.python = Path(python or sys.executable)
        self.renderer = NativeRendererProcess(
            renderer_executable(self.root), diagnostics, popen=popen)
        self.tuner_process = None

    def open_renderer(self):
        if self.renderer.process is not None and self.renderer.process.poll() is None:
            return False, 'already_running'
        if not self.renderer.executable.is_file():
            self.renderer._record_failure('renderer_executable_missing')
            return False, 'missing_executable'
        return ((True, 'started') if self.renderer.start()
                else (False, 'launch_failed'))

    def open_tuner(self):
        started, reason = self.open_renderer()
        if not started and reason != 'already_running':
            return False, reason
        if self.tuner_process is not None and self.tuner_process.poll() is None:
            return False, 'tuner_already_running'
        self.tuner_process = None
        try:
            self.tuner_process = self.popen(
                [str(self.python), '-m', 'oes_core_renderer.tuning_panel'],
                cwd=str(self.root), stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except OSError:
            self.tuner_process = None
            if started:
                self.renderer.close()
            return False, 'tuner_launch_failed'
        return True, 'started'

    def close_renderer(self):
        self.renderer.close()

    def close_all(self):
        tuner, self.tuner_process = self.tuner_process, None
        if tuner is not None and tuner.poll() is None:
            tuner.terminate()
            try:
                tuner.wait(timeout=2)
            except subprocess.TimeoutExpired:
                tuner.kill()
        self.renderer.close()
