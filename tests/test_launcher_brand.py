import unittest
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree

from PIL import Image

from oes_core_launcher.launch import launch_is_ready, reduced_motion_enabled
from tools.build_oes_core_icon import (
    BASE_LAUNCH,
    WEBSITE_EYEBALL,
    aspect_fit_eyeball,
)


class LauncherBrandTests(unittest.TestCase):
    def test_website_eyeball_is_the_unchanged_aspect_fit_source(self):
        svg = ElementTree.parse(WEBSITE_EYEBALL).getroot()
        self.assertEqual(svg.attrib['width'], '220')
        self.assertEqual(svg.attrib['height'], '220')
        self.assertEqual(svg.attrib['viewBox'], '0 0 220 220')
        expected = aspect_fit_eyeball(512, .7)
        with Image.open(BASE_LAUNCH) as launch:
            self.assertEqual(launch.convert('RGBA').tobytes(), expected.tobytes())
        source_dir = BASE_LAUNCH.parent / 'source'
        self.assertFalse((source_dir / 'eyeball-base-master.png').exists())
        self.assertFalse((source_dir / 'eyeball-baseball-master.png').exists())

    def test_icon_contains_every_windows_size_and_launch_assets(self):
        root = Path(__file__).resolve().parent.parent
        with Image.open(root / 'oes_core_launcher' / 'assets' / 'oes-eyeball.ico') as icon:
            self.assertEqual(
                icon.info['sizes'],
                {(16, 16), (20, 20), (24, 24), (32, 32), (40, 40),
                 (48, 48), (64, 64), (128, 128), (256, 256)},
            )
        for filename in ('eyeball-base-launch.png', 'eyeball-baseball-launch.png'):
            with Image.open(root / 'oes_core_launcher' / 'assets' / filename) as image:
                self.assertEqual(image.size, (512, 512))
                self.assertEqual(image.mode, 'RGBA')
                self.assertEqual(image.getchannel('A').getextrema(), (0, 255))

    def test_launch_respects_reduced_motion_and_waits_for_ready_state(self):
        self.assertTrue(reduced_motion_enabled('win32', lambda: False))
        self.assertFalse(reduced_motion_enabled('win32', lambda: True))
        self.assertFalse(reduced_motion_enabled('darwin', lambda: False))
        self.assertFalse(launch_is_ready(SimpleNamespace(core='Starting')))
        self.assertTrue(launch_is_ready(SimpleNamespace(core='Online')))
        self.assertTrue(launch_is_ready(SimpleNamespace(core='Needs Attention')))


if __name__ == '__main__':
    unittest.main()
