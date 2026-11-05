import json
import tempfile
import unittest
from pathlib import Path

from oes_core_renderer.character_animation import STATES, CharacterPose, sample_pose
from oes_core_renderer.gltf_pipeline import REQUIRED_NODE_NAMES, validate_gltf
from oes_core_renderer.character_preview import preview_command, renderer_path
from oes_core_renderer.themes import load_theme


class EyeballCharacterSystemTests(unittest.TestCase):
    def test_preview_resolves_only_the_isolated_worktree_build(self):
        root = Path(r'C:\OES\CharacterWorktree')
        self.assertEqual(renderer_path(root), root / 'build' / 'oes-core-renderer' /
                         'Release' / 'oes-eyeball-renderer.exe')
        command = preview_command(root / 'renderer.exe', root / 'diagnostics.json',
                                  root / 'control.json', 'side', 'scan', True, True)
        self.assertEqual(command[0], str(root / 'renderer.exe'))
        self.assertEqual(command[command.index('--view') + 1], 'side')
        self.assertEqual(command[command.index('--animation') + 1], 'scan')
        self.assertIn('--reduced-motion', command)
        self.assertIn('--force-warp', command)

    def test_animation_states_are_bounded_frame_rate_independent_samples(self):
        for state in STATES:
            first = sample_pose(state, 1.25)
            second = sample_pose(state, 1.25)
            self.assertEqual(first, second)
            self.assertGreaterEqual(first.aperture, 0.0)
            self.assertLessEqual(first.aperture, 1.0)
            self.assertGreater(first.pupil_scale, 0.0)
        with self.assertRaises(ValueError):
            sample_pose('spin', 0)
        with self.assertRaises(ValueError):
            sample_pose('idle', -1)

    def test_blink_focus_and_scan_change_only_bounded_character_pose(self):
        blink_samples = [sample_pose('blink', value / 100) for value in range(300)]
        self.assertLess(min(item.aperture for item in blink_samples), .2)
        focus_samples = [sample_pose('focus', value / 10) for value in range(30)]
        self.assertLess(min(item.pupil_scale for item in focus_samples),
                        max(item.pupil_scale for item in focus_samples))
        scan = sample_pose('scan', .75)
        self.assertGreaterEqual(scan.scan, 0)
        self.assertLessEqual(scan.scan, 1)
        scan_rest = sample_pose('scan', 2.0)
        self.assertEqual(scan_rest.scan, .5)
        self.assertEqual(scan_rest.gaze_x, 0)

    def test_reduced_motion_returns_stable_canonical_pose(self):
        self.assertEqual(sample_pose('idle', 1, True), CharacterPose())
        self.assertEqual(sample_pose('blink', 999, True), CharacterPose())
        self.assertEqual(sample_pose('scan', 4, True), CharacterPose())

    def test_theme_manifests_are_strict_and_placeholders_remain_reserved(self):
        root = Path(__file__).resolve().parents[1] / 'oes_core_renderer' / 'themes'
        default = load_theme(root / 'default.json')
        minimal = load_theme(root / 'pirate-minimal.json')
        full = load_theme(root / 'pirate-full.json')
        self.assertEqual(default['status'], 'complete')
        self.assertEqual(minimal['status'], 'reserved')
        self.assertEqual(full['status'], 'reserved')
        self.assertEqual(default['accessories'], [])

    def test_theme_schema_rejects_unknown_fields_and_completed_placeholders(self):
        root = Path(__file__).resolve().parents[1] / 'oes_core_renderer' / 'themes'
        value = json.loads((root / 'pirate-minimal.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'theme.json'
            path.write_text(json.dumps(dict(value, network_url='https://example.test')),
                            encoding='utf-8')
            with self.assertRaises(ValueError):
                load_theme(path)
            value['status'] = 'complete'
            path.write_text(json.dumps(value), encoding='utf-8')
            with self.assertRaises(ValueError):
                load_theme(path)

    def test_gltf_validator_preserves_required_movable_hierarchy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'character.bin').write_bytes(b'\0' * 16)
            value = {
                'asset': {'version': '2.0'},
                'nodes': [{'name': name, 'mesh': 0} for name in sorted(REQUIRED_NODE_NAMES)],
                'meshes': [{'name': 'character', 'primitives': []}],
                'materials': [{'name': 'metal'}],
                'buffers': [{'uri': 'character.bin', 'byteLength': 16}],
            }
            path = root / 'character.gltf'
            path.write_text(json.dumps(value), encoding='utf-8')
            result = validate_gltf(path)
            self.assertEqual(result['nodes'], len(REQUIRED_NODE_NAMES))

    def test_gltf_validator_rejects_missing_parts_remote_and_traversal_buffers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = {'asset': {'version': '2.0'}, 'nodes': [], 'meshes': [],
                    'materials': [], 'buffers': []}
            path = root / 'character.gltf'
            path.write_text(json.dumps(base), encoding='utf-8')
            with self.assertRaises(ValueError):
                validate_gltf(path)
            base['nodes'] = [{'name': name} for name in REQUIRED_NODE_NAMES]
            base['buffers'] = [{'uri': 'https://example.test/character.bin'}]
            path.write_text(json.dumps(base), encoding='utf-8')
            with self.assertRaises(ValueError):
                validate_gltf(path)
            base['buffers'] = [{'uri': '../outside.bin'}]
            path.write_text(json.dumps(base), encoding='utf-8')
            with self.assertRaises(ValueError):
                validate_gltf(path)


if __name__ == '__main__':
    unittest.main()
