import io
import json
import os
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from oes_core_launcher.config import LauncherConfig
from oes_core_launcher.controller import (CoreController, probe_ollama,
                                           start_ollama_application)
from oes_core_launcher.instance import SingleInstance
from oes_core_launcher.install_shortcut import shortcut_metadata, shortcut_script
from oes_core_launcher.provision import (INVALID, MISMATCH, SAVE_FAILED, SUCCESS,
                                         ProvisioningSession)


DIGEST = 'ab' * 32


def config():
    return LauncherConfig('razer-beta', 'beta-1',
                          'https://otisexecutionsystems.com', DIGEST)


class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *args): self.close()


class SequenceOpener:
    def __init__(self, values): self.values = iter(values)
    def open(self, request, timeout):
        value = next(self.values)
        if isinstance(value, Exception): raise value
        return Response(json.dumps(value).encode())


class FakeProcess:
    def __init__(self, command, **kwargs):
        self.command, self.kwargs = command, kwargs
        self.stdin = io.StringIO()
        self.stderr = io.StringIO('')
        self.code = None
        self.terminated = False
    def poll(self): return self.code
    def wait(self, timeout=None): self.code = 0; return 0
    def terminate(self): self.terminated = True; self.code = -1
    def kill(self): self.code = -9


class Store:
    def __init__(self, value): self.value = value
    def read(self): return self.value


class RecordingCredentialStore:
    def __init__(self, error=None):
        self.error = error
        self.writes = []
    def write(self, secret, worker_id):
        if self.error:
            raise self.error
        self.writes.append((secret, worker_id))


class LauncherTests(unittest.TestCase):
    def launcher(self, root, worker_popen, starter, statuses=None):
        return CoreController(lambda: config(), Store('cd'*32), root, worker_popen,
                              (statuses if statuses is not None else []).append,
                              poll_seconds=60,
                              ollama_starter=starter, readiness_attempts=2,
                              readiness_interval=0, readiness_sleep=lambda _: None)

    def test_provisioning_matching_values_save_once(self):
        store = RecordingCredentialStore()
        session = ProvisioningSession(config(), store)
        secret = 'cd' * 32
        self.assertEqual(session.save(secret, secret), (True, SUCCESS))
        self.assertEqual(store.writes, [(secret, config().worker_id)])

    def test_provisioning_mismatch_invalid_and_cancel_save_nothing(self):
        for first, second, expected in (
                ('cd' * 32, 'ef' * 32, MISMATCH),
                ('not-a-valid-key', 'not-a-valid-key', INVALID)):
            with self.subTest(expected=expected):
                store = RecordingCredentialStore()
                session = ProvisioningSession(config(), store)
                self.assertEqual(session.save(first, second), (False, expected))
                self.assertEqual(store.writes, [])
        store = RecordingCredentialStore()
        session = ProvisioningSession(config(), store)
        self.assertFalse(session.cancel())
        self.assertEqual(store.writes, [])

    def test_provisioning_never_exposes_secret_in_messages_or_output(self):
        secret = 'cd' * 32
        store = RecordingCredentialStore(ValueError(secret))
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            result = ProvisioningSession(config(), store).save(secret, secret)
        self.assertEqual(result, (False, SAVE_FAILED))
        self.assertNotIn(secret, output.getvalue())
        self.assertNotIn(secret, repr(result))

    def test_configuration_validation_and_loading(self):
        config().validate()
        for changes in ({'relay_url':'http://example.com'}, {'ollama_url':'http://localhost:11434'},
                        {'model_digest':'bad'}, {'worker_id':'bad id'}):
            with self.subTest(changes=changes):
                values = config().__dict__ | changes
                with self.assertRaises(ValueError): LauncherConfig(**values).validate()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            path.write_text(json.dumps(config().__dict__), encoding='utf-8')
            self.assertEqual(LauncherConfig.load(path), config())

    def test_secret_absence_stops_before_process_and_never_leaks(self):
        popen = Mock()
        statuses = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); executable = root/'.venv'/'Scripts'/'python.exe'
            executable.parent.mkdir(parents=True); executable.touch()
            controller = CoreController(lambda: config(), Store(None), root, popen,
                                        statuses.append, poll_seconds=60)
            with patch('oes_core_launcher.controller.probe_ollama',
                       return_value='Available; llama3.2 unloaded'):
                self.assertFalse(controller.start())
        popen.assert_not_called()
        self.assertEqual(statuses[-1].core, 'Needs Attention')
        self.assertNotIn('None', statuses[-1].detail)

    def test_start_stop_restart_and_no_secret_in_arguments(self):
        processes = []
        def spawn(*args, **kwargs):
            process = FakeProcess(*args, **kwargs); processes.append(process); return process
        statuses = []
        secret = 'cd' * 32
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); executable = root/'.venv'/'Scripts'/'python.exe'
            executable.parent.mkdir(parents=True); executable.touch()
            controller = CoreController(lambda: config(), Store(secret), root, spawn,
                                        statuses.append, poll_seconds=60)
            with patch('oes_core_launcher.controller.probe_ollama',
                       return_value='Available; llama3.2 unloaded'):
                self.assertTrue(controller.start())
                self.assertFalse(controller.start())
                self.assertEqual(processes[0].command, [str(executable), '-m', 'worker'])
                self.assertNotIn(secret, str(processes[0].command))
                self.assertEqual(processes[0].kwargs['env']['OES_WORKER_SHARED_KEY'], secret)
                controller.stop()
                self.assertEqual(processes[0].stdin.getvalue(), 'STOP\n')
                self.assertTrue(controller.restart())
                controller.close()
        self.assertEqual(len(processes), 2)
        self.assertEqual(statuses[-1].worker, 'Stopped')
        self.assertNotIn(secret, repr(statuses))

    def test_ollama_ready_does_not_restart_and_worker_starts(self):
        worker_popen = Mock(return_value=FakeProcess(['python']))
        starter = Mock()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); executable = root/'.venv'/'Scripts'/'python.exe'
            executable.parent.mkdir(parents=True); executable.touch()
            controller = self.launcher(root, worker_popen, starter)
            with patch('oes_core_launcher.controller.probe_ollama',
                       return_value='Available; llama3.2 unloaded'):
                self.assertTrue(controller.start())
                controller.close()
        starter.assert_not_called()
        worker_popen.assert_called_once()

    def test_ollama_cold_start_waits_then_starts_worker(self):
        worker_popen = Mock(return_value=FakeProcess(['python']))
        starter = Mock()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); executable = root/'.venv'/'Scripts'/'python.exe'
            executable.parent.mkdir(parents=True); executable.touch()
            controller = self.launcher(root, worker_popen, starter)
            with patch('oes_core_launcher.controller.probe_ollama',
                       side_effect=['Unavailable', 'Unavailable',
                                    'Available; llama3.2 unloaded']):
                self.assertTrue(controller.start())
                controller.close()
        starter.assert_called_once_with()
        worker_popen.assert_called_once()

    def test_ollama_never_ready_fails_without_worker(self):
        worker_popen = Mock()
        starter = Mock()
        statuses = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); executable = root/'.venv'/'Scripts'/'python.exe'
            executable.parent.mkdir(parents=True); executable.touch()
            controller = self.launcher(root, worker_popen, starter, statuses)
            with patch('oes_core_launcher.controller.probe_ollama',
                       return_value='Unavailable'):
                self.assertFalse(controller.start())
        starter.assert_called_once_with()
        worker_popen.assert_not_called()
        self.assertEqual(statuses[-1].detail,
                         'Ollama did not become ready within the startup window')

    def test_cold_start_wrong_model_digest_remains_hard_failure(self):
        worker_popen = Mock()
        starter = Mock()
        statuses = []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); executable = root/'.venv'/'Scripts'/'python.exe'
            executable.parent.mkdir(parents=True); executable.touch()
            controller = self.launcher(root, worker_popen, starter, statuses)
            with patch('oes_core_launcher.controller.probe_ollama',
                       side_effect=['Unavailable',
                                    'Available; required model or digest missing']):
                self.assertFalse(controller.start())
        starter.assert_called_once_with()
        worker_popen.assert_not_called()
        self.assertEqual(statuses[-1].detail,
                         'Required Ollama model or digest is unavailable')

    def test_restart_uses_same_ollama_readiness_path(self):
        processes = []
        def spawn(*args, **kwargs):
            process = FakeProcess(*args, **kwargs); processes.append(process); return process
        starter = Mock()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); executable = root/'.venv'/'Scripts'/'python.exe'
            executable.parent.mkdir(parents=True); executable.touch()
            controller = self.launcher(root, spawn, starter)
            with patch('oes_core_launcher.controller.probe_ollama', side_effect=[
                    'Available; llama3.2 unloaded', 'Unavailable',
                    'Available; llama3.2 unloaded']):
                self.assertTrue(controller.start())
                self.assertTrue(controller.restart())
                controller.close()
        self.assertEqual(len(processes), 2)
        starter.assert_called_once_with()

    def test_ollama_application_uses_per_user_location(self):
        launched = Mock()
        with tempfile.TemporaryDirectory() as directory:
            local = Path(directory)
            executable = local/'Programs'/'Ollama'/'ollama app.exe'
            executable.parent.mkdir(parents=True); executable.touch()
            start_ollama_application({'LOCALAPPDATA':str(local)}, launched)
        command = launched.call_args.args[0]
        self.assertEqual(command, [str(executable)])
        self.assertNotIn('OES_WORKER_SHARED_KEY', repr(launched.call_args))

    def test_post_spawn_failure_cleans_up_owned_process_before_clearing(self):
        processes = []
        ownership_during_cleanup = []
        controller = None

        class ObservedProcess(FakeProcess):
            def wait(self, timeout=None):
                ownership_during_cleanup.append(controller.process is self)
                return super().wait(timeout)

        def spawn(*args, **kwargs):
            process = ObservedProcess(*args, **kwargs)
            processes.append(process)
            return process

        def callback(status):
            if status.core == 'Online':
                raise RuntimeError('status callback failed')

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); executable = root/'.venv'/'Scripts'/'python.exe'
            executable.parent.mkdir(parents=True); executable.touch()
            controller = CoreController(lambda: config(), Store('cd'*32), root, spawn,
                                        callback, poll_seconds=60)
            with patch('oes_core_launcher.controller.probe_ollama',
                       return_value='Available; llama3.2 unloaded'):
                self.assertFalse(controller.start())

        self.assertEqual(len(processes), 1)
        self.assertEqual(processes[0].stdin.getvalue(), 'STOP\n')
        self.assertEqual(ownership_during_cleanup, [True])
        self.assertIsNone(controller.process)
        self.assertFalse(processes[0].terminated)

    def test_unexpected_exit_becomes_needs_attention(self):
        process = FakeProcess(['python'])
        process.code = 1
        statuses = []
        controller = CoreController(lambda: config(), Store('cd'*32), callback=statuses.append)
        controller.process = process
        controller._watch()
        self.assertEqual(statuses[-1].core, 'Needs Attention')
        self.assertEqual(statuses[-1].worker, 'Exited')

    def test_status_reader_uses_only_fixed_diagnostics(self):
        process = FakeProcess(['python'])
        process.stderr = io.StringIO('private arbitrary text\nWARNING worker relay connected\n')
        statuses = []
        controller = CoreController(callback=statuses.append)
        controller._read_status(process)
        self.assertEqual(statuses[-1].relay, 'Connected')
        self.assertNotIn('private arbitrary text', repr(statuses))

    def test_ollama_unavailable_unloaded_and_loaded(self):
        unavailable = SequenceOpener([OSError('down')])
        self.assertEqual(probe_ollama(config(), unavailable), 'Unavailable')
        tags = {'models':[{'name':'llama3.2:latest','digest':DIGEST}]}
        self.assertEqual(probe_ollama(config(), SequenceOpener([tags, {'models':[]}])) ,
                         'Available; llama3.2 unloaded')
        running = {'models':[{'name':'llama3.2:latest'}]}
        self.assertEqual(probe_ollama(config(), SequenceOpener([tags, running])),
                         'Available; llama3.2 loaded')

    def test_duplicate_instance_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'launcher.lock'
            first, second = SingleInstance(path), SingleInstance(path)
            self.assertTrue(first.acquire())
            self.assertFalse(second.acquire())
            first.release()
            self.assertTrue(second.acquire())
            second.release()

    def test_shortcut_contains_no_secret_or_worker_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pythonw = root/'.venv'/'Scripts'/'pythonw.exe'
            icon = root/'oes_core_launcher'/'assets'/'oes-eyeball.ico'
            pythonw.parent.mkdir(parents=True); pythonw.touch()
            icon.parent.mkdir(parents=True); icon.touch()
            script = shortcut_script(root)
            metadata = shortcut_metadata(root)
        self.assertEqual(metadata, {
            'target': str(pythonw),
            'arguments': '-m oes_core_launcher',
            'working_directory': str(root),
            'icon': str(icon) + ',0',
            'description': 'OES Core / Eyeball',
        })
        self.assertIn("GetFolderPath('Desktop')", script)
        self.assertIn("GetFolderPath('Startup')", script)
        self.assertEqual(script.count("'OES Core.lnk'"), 2)
        for name in ('OES_WORKER_SHARED_KEY', 'OES_WORKER_ID', 'OES_WORKER_RELAY_URL'):
            self.assertNotIn(name, script + repr(metadata))
        self.assertNotIn("-m worker", script)
        self.assertNotIn('ollama app', script.lower())

    def test_shortcut_installation_is_idempotent_and_does_not_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pythonw = root/'.venv'/'Scripts'/'pythonw.exe'
            icon = root/'oes_core_launcher'/'assets'/'oes-eyeball.ico'
            pythonw.parent.mkdir(parents=True); pythonw.touch()
            icon.parent.mkdir(parents=True); icon.touch()
            first = shortcut_script(root)
            second = shortcut_script(root)
        self.assertEqual(first, second)
        self.assertEqual(first.count('$shell.CreateShortcut($path)'), 1)
        self.assertEqual(first.count('Install-OesCoreShortcut (Join-Path'), 2)
        self.assertNotIn('Start-Process', first)


if __name__ == '__main__':
    unittest.main()
