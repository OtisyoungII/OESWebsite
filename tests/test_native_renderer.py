import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from oes_core_launcher.renderer_process import (RENDERER_BUILD_COMMAND,
                                                 NativeEyeballManager,
                                                 NativeRendererProcess,
                                                 renderer_executable)
from oes_core_renderer.preview_host import (NativePreviewHost, WS_CHILD,
                                             WS_OVERLAPPEDWINDOW, WS_POPUP,
                                             WS_VISIBLE)
from oes_core_renderer.tuning import (CANONICAL_PARAMETERS, default_paths,
                                      load_preset, read_diagnostics,
                                      read_parameters, save_preset,
                                      validate_parameters, write_parameters)


class NativeRendererTests(unittest.TestCase):
    def test_launcher_resolves_only_renderer_from_its_own_checkout(self):
        root = Path(r'C:\OES\RepairCheckout')
        self.assertEqual(
            renderer_executable(root),
            root / 'build' / 'oes-core-renderer' / 'Release' / 'oes-eyeball-renderer.exe')
        self.assertIn('cmake --build build/oes-core-renderer --config Release',
                      RENDERER_BUILD_COMMAND)

    def test_launcher_prevents_duplicate_renderer_and_tuner_processes(self):
        class Process:
            def __init__(self, command):
                self.command, self.returncode = command, None
            def poll(self): return self.returncode
            def terminate(self): self.returncode = 0
            def wait(self, timeout=None): return self.returncode
            def kill(self): self.returncode = -9

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = renderer_executable(root)
            executable.parent.mkdir(parents=True)
            executable.touch()
            calls = []
            def popen(command, **_kwargs):
                calls.append(command)
                return Process(command)
            manager = NativeEyeballManager(
                root, root / 'diagnostics.json', popen, root / 'pythonw.exe')
            self.assertEqual(manager.open_renderer(), (True, 'started'))
            self.assertEqual(manager.open_renderer(), (False, 'already_running'))
            self.assertEqual(manager.open_tuner(), (True, 'started'))
            self.assertEqual(manager.open_tuner(), (False, 'tuner_already_running'))
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0][0], str(executable))
            self.assertEqual(calls[1][1:], ['-m', 'oes_core_renderer.tuning_panel'])

    def test_launcher_missing_renderer_does_not_search_or_start_tuner(self):
        with tempfile.TemporaryDirectory() as directory:
            popen = Mock()
            root = Path(directory)
            manager = NativeEyeballManager(root, root / 'diagnostics.json', popen)
            self.assertEqual(manager.open_renderer(), (False, 'missing_executable'))
            self.assertEqual(manager.open_tuner(), (False, 'missing_executable'))
            popen.assert_not_called()

    def test_launcher_closes_only_its_owned_renderer_and_tuner(self):
        process = Mock()
        process.poll.return_value = None
        manager = NativeEyeballManager(Path.cwd(), Path('diagnostics.json'))
        manager.renderer.process = process
        tuner = Mock()
        tuner.poll.return_value = None
        manager.tuner_process = tuner
        manager.close_all()
        tuner.terminate.assert_called_once_with()
        process.terminate.assert_called_once_with()
        self.assertIsNone(manager.renderer.process)
        self.assertIsNone(manager.tuner_process)

    def test_existing_oes_core_ui_exposes_native_actions_without_replacing_shortcut(self):
        root = Path(__file__).resolve().parents[1]
        ui = (root / 'oes_core_launcher' / 'ui.py').read_text(encoding='utf-8')
        shortcut = (root / 'oes_core_launcher' / 'install_shortcut.py').read_text(
            encoding='utf-8')
        for label in ('Open 3D Eyeball', 'Open 3D Tuner', 'Close Eyeball'):
            self.assertIn(label, ui)
        self.assertIn("'OES Core.lnk'", shortcut)
        self.assertNotIn('3D Eyeball.lnk', shortcut)

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

    def test_renderer_build_uses_canonical_identity_only_on_3d_logo_plane(self):
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
        self.assertIn('"oes_identity"', source)
        self.assertIn('native_character_animated', source)
        self.assertNotIn('TRIANGLESTRIP', source)
        self.assertNotIn('three.js', source.lower())
        self.assertNotIn('THREE.', source)

    def test_canonical_tuning_values_reproduce_static_3d_reference(self):
        self.assertEqual(CANONICAL_PARAMETERS['scale'], 1.0)
        self.assertEqual(CANONICAL_PARAMETERS['width'], 512)
        self.assertEqual(CANONICAL_PARAMETERS['height'], 512)
        self.assertEqual(CANONICAL_PARAMETERS['rotation_x'], 0.0)
        self.assertEqual(CANONICAL_PARAMETERS['rotation_y'], 0.0)
        self.assertEqual(CANONICAL_PARAMETERS['rotation_z'], 0.0)
        self.assertEqual(CANONICAL_PARAMETERS['brightness'], 1.0)
        self.assertEqual(CANONICAL_PARAMETERS['exposure'], 0.92)
        self.assertEqual(CANONICAL_PARAMETERS['lighting_intensity'], 1.0)
        self.assertEqual(CANONICAL_PARAMETERS['camera_fov'], 50.0)
        self.assertEqual(CANONICAL_PARAMETERS['camera_z'], 7.4)
        for name in ('iris_scale', 'pupil_scale', 'glass_intensity',
                     'rim_intensity', 'orbit_intensity', 'particle_intensity',
                     'logo_scale'):
            self.assertEqual(CANONICAL_PARAMETERS[name], 1.0)

    def test_parameter_snapshots_and_presets_round_trip_without_artwork(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control = root / 'control.json'
            preset = root / 'preset.json'
            changed = dict(CANONICAL_PARAMETERS, scale=1.12, rotation_y=15.0,
                           glass_intensity=.4, width=640, height=480)
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

    def test_geometry_hierarchy_and_canonical_dimensions_are_present(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / 'oes_core_renderer' / 'src' / 'main.cpp').read_text(encoding='utf-8')
        for component in (
            'mechanical_body', 'recessed_core', 'energy_lattice', 'optical_glass',
            'housing_seam', 'front_housing', 'body_rib', 'aperture_blade',
            'layered_iris', 'iris_focusing_ring', 'recessed_pupil', 'pupil_light_ring',
            'oes_identity', 'orbit_outer',
            'orbit_middle', 'orbit_inner', 'orbit_node', 'particles',
        ):
            self.assertIn(f'"{component}"', source)
        for dimension in ('sphere(1.18f,112,96)', 'sphere(1.135f,96,80)',
                          'icosphere_lines(1.158f,5)', 'sphere(1.205f,96,80)',
                          'spherical_annulus(1.203f,.225f,.565f,128,32)',
                          'spherical_cap(1.187f,.235f,112,24)'):
            self.assertIn(dimension, source)

    def test_curved_face_geometry_has_radial_normals_and_outward_identity_uv(self):
        root = Path(__file__).resolve().parents[1]
        geometry = (root / 'oes_core_renderer' / 'src' / 'scene_geometry.h').read_text(
            encoding='utf-8')
        source = (root / 'oes_core_renderer' / 'src' / 'main.cpp').read_text(
            encoding='utf-8')
        self.assertIn('MeshData spherical_annulus', geometry)
        self.assertIn('const Vec3 normal{radial * std::cos(theta)', geometry)
        self.assertIn('normal.z * radius', geometry)
        self.assertIn('{a, a + 1, b, a + 1, b + 1, b}', geometry)
        self.assertIn('result.indices = {0, 2, 1, 0, 3, 2}', geometry)
        self.assertIn('MeshData spherical_cap', geometry)
        self.assertIn('outward_identity_plane', geometry)
        self.assertIn('MeshData aperture_blade', geometry)
        self.assertIn('vertex.u = 1.0f - vertex.u', geometry)
        self.assertIn('outward_identity_plane(.45f,.45f)', source)
        self.assertNotIn('XMMatrixScaling(parameters_.iris_scale,parameters_.iris_scale,.18f)',
                         source)

    def test_native_window_has_normal_close_escape_and_no_toolwindow_topmost_style(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / 'oes_core_renderer' / 'src' / 'main.cpp').read_text(
            encoding='utf-8')
        self.assertIn('WS_OVERLAPPEDWINDOW', source)
        self.assertIn('WS_EX_APPWINDOW|WS_EX_NOREDIRECTIONBITMAP', source)
        self.assertNotIn('WS_EX_TOOLWINDOW', source)
        self.assertNotIn('HWND_TOPMOST', source)
        self.assertIn('message==WM_CLOSE', source)
        self.assertIn('wparam==VK_ESCAPE&&!GetParent(window)', source)

    def test_geometry_generators_are_indexed_and_particles_are_deterministic(self):
        root = Path(__file__).resolve().parents[1]
        geometry = (root / 'oes_core_renderer' / 'src' / 'scene_geometry.h').read_text(
            encoding='utf-8')
        source = (root / 'oes_core_renderer' / 'src' / 'main.cpp').read_text(encoding='utf-8')
        self.assertIn('std::mt19937 random(seed)', geometry)
        self.assertIn('particles(110,0x004f4553u,1.46f,2.71f)', source)
        self.assertIn('result.indices.insert', geometry)
        self.assertIn('D3D11_PRIMITIVE_TOPOLOGY_POINTLIST', source)

    def test_character_animation_is_state_driven_restrained_and_reduced_motion_aware(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / 'oes_core_renderer' / 'src' / 'main.cpp').read_text(encoding='utf-8')
        character = (root / 'oes_core_renderer' / 'src' / 'character_system.h').read_text(
            encoding='utf-8')
        self.assertIn('AnimationController', source)
        self.assertIn('reduced_motion_enabled()', source)
        for state in ('idle', 'blink', 'focus', 'scan'):
            self.assertIn(state, character)
        self.assertNotIn('spin', character.lower())

    def test_transposed_directx_matrices_use_row_vector_hlsl_convention(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / 'oes_core_renderer' / 'src' / 'main.cpp').read_text(encoding='utf-8')
        self.assertIn('XMMatrixTranspose(world)', source)
        self.assertIn('XMMatrixTranspose(view*projection)', source)
        self.assertIn('mul(float4(v.position,1),world)', source)
        self.assertIn('mul(p,view_projection)', source)
        self.assertNotIn('mul(world,float4(v.position,1))', source)

    def test_renderer_source_uses_file_snapshots_without_network_listener(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / 'oes_core_renderer' / 'src' / 'main.cpp').read_text(encoding='utf-8')
        panel = (root / 'oes_core_renderer' / 'tuning_panel.py').read_text(encoding='utf-8')
        self.assertIn('renderer-tuning.json', source)
        self.assertIn('read_parameters(control,', source)
        self.assertIn('PeekMessageW', source)
        self.assertIn('renderer-diagnostics.json', source)
        self.assertNotIn('winsock', source.lower())
        self.assertNotIn('socket', panel.lower())

    def test_visual_tuner_hosts_real_renderer_and_restores_standalone_window(self):
        class FakePreviewApi:
            def __init__(self):
                self.renderer = 91
                self.parents = []
                self.styles = []
                self.positions = []
                self.invalidations = []
                self.closed = []

            def find_renderer(self):
                return self.renderer

            @staticmethod
            def parent(_hwnd):
                return 0

            @staticmethod
            def style(_hwnd):
                return WS_OVERLAPPEDWINDOW | WS_VISIBLE

            @staticmethod
            def rect(_hwnd):
                return 40, 50, 512, 512

            def set_style(self, hwnd, style):
                self.styles.append((hwnd, style))

            def set_parent(self, hwnd, parent):
                self.parents.append((hwnd, parent))

            def position(self, hwnd, x, y, width, height):
                self.positions.append((hwnd, x, y, width, height))

            def invalidate(self, hwnd):
                self.invalidations.append(hwnd)

            def close(self, hwnd):
                self.closed.append(hwnd)

        api = FakePreviewApi()
        preview = NativePreviewHost(api)
        self.assertTrue(preview.attach(700))
        self.assertEqual(api.parents[-1], (91, 700))
        self.assertTrue(api.styles[-1][1] & WS_CHILD)
        self.assertFalse(api.styles[-1][1] & WS_POPUP)
        self.assertFalse(api.styles[-1][1] & WS_OVERLAPPEDWINDOW)
        self.assertTrue(preview.place(700, 650, 512, 512))
        self.assertEqual(api.positions[-1], (91, 94, 69, 512, 512))
        self.assertEqual(api.invalidations[-1], 700)
        self.assertTrue(preview.detach())
        self.assertEqual(api.parents[-1], (91, 0))
        self.assertTrue(api.styles[-1][1] & WS_OVERLAPPEDWINDOW)
        self.assertEqual(api.positions[-1], (91, 40, 50, 512, 512))
        self.assertEqual(api.invalidations[-1], 700)
        self.assertFalse(preview.attached)

        self.assertTrue(preview.attach(700))
        self.assertTrue(preview.close_renderer())
        self.assertEqual(api.closed, [91])
        self.assertFalse(preview.attached)

    def test_visual_tuner_does_not_require_renderer_or_change_native_source(self):
        class MissingPreviewApi:
            @staticmethod
            def find_renderer():
                return 0

        preview = NativePreviewHost(MissingPreviewApi())
        self.assertFalse(preview.attach(700))
        self.assertFalse(preview.attached)
        root = Path(__file__).resolve().parents[1]
        panel = (root / 'oes_core_renderer' / 'tuning_panel.py').read_text(encoding='utf-8')
        host = (root / 'oes_core_renderer' / 'preview_host.py').read_text(encoding='utf-8')
        self.assertIn('Live native preview', panel)
        self.assertIn('SetParent', host)
        self.assertNotIn('Canvas.create_oval', panel)

    def test_transparent_preview_surface_has_no_stale_placeholder_content(self):
        root = Path(__file__).resolve().parents[1]
        panel = (root / 'oes_core_renderer' / 'tuning_panel.py').read_text(encoding='utf-8')
        self.assertIn('self.preview_message = None', panel)
        self.assertNotIn('Waiting for the native renderer', panel)
        self.assertNotIn('preview_message.place', panel)


if __name__ == '__main__':
    unittest.main()
