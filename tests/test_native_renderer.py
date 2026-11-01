import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from oes_core_launcher.renderer_process import NativeRendererProcess


class NativeRendererTests(unittest.TestCase):
    def test_missing_or_failed_renderer_preserves_launcher_process(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            boundary = NativeRendererProcess(root / 'missing.exe', root / 'diagnostics.json')
            self.assertFalse(boundary.start())
            self.assertIsNone(boundary.process)
            self.assertEqual(boundary.status(), {
                'status': 'failed', 'reason': 'renderer_executable_missing'
            })

            executable = root / 'renderer.exe'
            executable.touch()
            popen = Mock(side_effect=OSError('graphics unavailable'))
            boundary = NativeRendererProcess(executable, root / 'diagnostics.json', popen)
            self.assertFalse(boundary.start())
            self.assertIsNone(boundary.process)
            self.assertEqual(boundary.status(), {
                'status': 'failed', 'reason': 'renderer_process_unavailable'
            })

    def test_diagnostics_are_read_without_exposing_renderer_internals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            diagnostics = root / 'diagnostics.json'
            expected = {
                'status': 'ready',
                'adapter_name': 'NVIDIA test adapter',
                'feature_level': '11_1',
                'device_type': 'hardware',
            }
            diagnostics.write_text(json.dumps(expected), encoding='utf-8')
            boundary = NativeRendererProcess(root / 'renderer.exe', diagnostics)
            self.assertEqual(boundary.status(), expected)

    def test_renderer_build_references_only_canonical_identity(self):
        root = Path(__file__).resolve().parents[1]
        canonical = root / 'static' / 'images' / 'oes-logo.svg'
        self.assertEqual(
            hashlib.sha256(canonical.read_bytes()).hexdigest(),
            '1ce89e6864b8d5799d4806228a3f71172f5bd3c7adaba7d1c8772127d702032b',
        )
        cmake = (root / 'oes_core_renderer' / 'CMakeLists.txt').read_text(encoding='utf-8')
        source = (root / 'oes_core_renderer' / 'src' / 'main.cpp').read_text(encoding='utf-8')
        self.assertIn('../static/images/oes-logo.svg', cmake)
        self.assertIn('oes-eyeball-source.png', cmake)
        self.assertIn('DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE', source)
        self.assertIn('DXGI_ALPHA_MODE_PREMULTIPLIED', source)
        self.assertIn('DCompositionCreateDevice', source)
        self.assertIn('RSSetViewports', source)
        self.assertIn('D3D_DRIVER_TYPE_WARP', source)
        self.assertNotIn('three', source.lower())


if __name__ == '__main__':
    unittest.main()
