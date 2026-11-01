import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from oes_core_launcher.renderer_process import NativeRendererProcess
from oes_core_renderer.tuning import (CANONICAL_PARAMETERS, default_paths,
                                      load_preset, read_diagnostics,
                                      read_parameters, save_preset,
                                      validate_parameters, write_parameters)


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
            hashlib.sha256(canonical.read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
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

    def test_canonical_tuning_values_reproduce_accepted_baseline(self):
        self.assertEqual(CANONICAL_PARAMETERS['scale'], 0.86)
        self.assertEqual(CANONICAL_PARAMETERS['width'], 512)
        self.assertEqual(CANONICAL_PARAMETERS['height'], 512)
        self.assertEqual(CANONICAL_PARAMETERS['rotation'], 0.0)
        self.assertEqual(CANONICAL_PARAMETERS['opacity'], 1.0)
        self.assertEqual(CANONICAL_PARAMETERS['glow_intensity'], 0.0)
        self.assertEqual(CANONICAL_PARAMETERS['glow_radius'], 0.0)
        self.assertEqual(CANONICAL_PARAMETERS['brightness'], 1.0)
        self.assertEqual(CANONICAL_PARAMETERS['exposure'], 0.0)
        self.assertEqual(CANONICAL_PARAMETERS['lighting_intensity'], 1.0)
        self.assertEqual(CANONICAL_PARAMETERS['depth'], 0.0)
        self.assertEqual(CANONICAL_PARAMETERS['perspective_x'], 0.0)
        self.assertEqual(CANONICAL_PARAMETERS['perspective_y'], 0.0)

    def test_parameter_snapshots_and_presets_round_trip_without_artwork(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control = root / 'control.json'
            preset = root / 'preset.json'
            changed = dict(CANONICAL_PARAMETERS, scale=1.12, rotation=15.0,
                           glow_intensity=.4, width=640, height=480)
            self.assertEqual(write_parameters(control, changed), changed)
            self.assertEqual(read_parameters(control), changed)
            self.assertEqual(save_preset(preset, changed), changed)
            self.assertEqual(load_preset(preset), changed)
            payload = json.loads(preset.read_text(encoding='utf-8'))
            self.assertEqual(set(payload), {'version', 'parameters'})
            self.assertNotIn('asset', payload)
            self.assertNotIn('svg', preset.read_text(encoding='utf-8').lower())

    def test_parameter_validation_is_bounded_and_rejects_unknown_fields(self):
        with self.assertRaises(ValueError):
            validate_parameters({'scale': 99})
        with self.assertRaises(ValueError):
            validate_parameters({'network_url': 1})
        with self.assertRaises(ValueError):
            validate_parameters({'opacity': True})

    def test_missing_control_file_returns_canonical_independent_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            first = read_parameters(Path(directory) / 'missing.json')
            first['scale'] = .2
            self.assertEqual(read_parameters(Path(directory) / 'missing.json'),
                             CANONICAL_PARAMETERS)

    def test_default_ipc_is_local_app_data_and_has_separate_directions(self):
        control, diagnostics = default_paths({'LOCALAPPDATA': r'C:\Local'})
        self.assertEqual(control, Path(r'C:\Local') / 'OES' / 'Core' / 'Renderer' /
                         'renderer-tuning.json')
        self.assertEqual(diagnostics, Path(r'C:\Local') / 'OES' / 'Core' / 'Renderer' /
                         'renderer-diagnostics.json')
        self.assertNotEqual(control, diagnostics)

    def test_diagnostics_reader_exposes_only_tuning_panel_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'diagnostics.json'
            path.write_text(json.dumps({
                'status': 'ready', 'adapter_name': 'NVIDIA test adapter',
                'device_type': 'hardware', 'feature_level': '11_1', 'fps': 60.0,
                'width': 512, 'height': 512, 'parameters': CANONICAL_PARAMETERS,
                'error': 'must not cross the panel boundary', 'working_set_bytes': 123,
            }), encoding='utf-8')
            value = read_diagnostics(path)
            self.assertNotIn('error', value)
            self.assertNotIn('working_set_bytes', value)
            self.assertEqual(value['adapter_name'], 'NVIDIA test adapter')

    def test_renderer_source_uses_file_snapshots_without_network_listener(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / 'oes_core_renderer' / 'src' / 'main.cpp').read_text(encoding='utf-8')
        panel = (root / 'oes_core_renderer' / 'tuning_panel.py').read_text(encoding='utf-8')
        self.assertIn('renderer-tuning.json', source)
        self.assertIn('read_parameters(control_path', source)
        self.assertIn('PeekMessageW', source)
        self.assertIn('renderer-diagnostics.json', source)
        self.assertNotIn('winsock', source.lower())
        self.assertNotIn('socket', panel.lower())


if __name__ == '__main__':
    unittest.main()
