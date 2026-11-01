"""Optional isolated process boundary for the native Eyeball proof of concept."""
import json
import subprocess
from pathlib import Path


class NativeRendererProcess:
    def __init__(self, executable, diagnostics, popen=subprocess.Popen):
        self.executable = Path(executable)
        self.diagnostics = Path(diagnostics)
        self.popen = popen
        self.process = None

    def start(self):
        if self.process is not None:
            return False
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
