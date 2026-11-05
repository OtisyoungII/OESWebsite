"""Isolated standalone preview entry point for Eyeball character development."""
import argparse
import subprocess
import tempfile
from pathlib import Path

from .character_animation import STATES

VIEWS = ('front', 'three-quarter', 'side')


def renderer_path(root=None):
    root = Path(root or Path(__file__).resolve().parents[1])
    return root / 'build' / 'oes-core-renderer' / 'Release' / 'oes-eyeball-renderer.exe'


def preview_command(executable, diagnostics, control, view='front', animation='idle',
                    reduced_motion=False, force_warp=False):
    if view not in VIEWS or animation not in STATES:
        raise ValueError('Unsupported preview mode')
    command = [str(executable), '--diagnostics', str(diagnostics), '--control', str(control),
               '--view', view, '--animation', animation]
    if reduced_motion:
        command.append('--reduced-motion')
    if force_warp:
        command.append('--force-warp')
    return command


def main(argv=None):
    parser = argparse.ArgumentParser(description='Preview the isolated native Eyeball character')
    parser.add_argument('--view', choices=VIEWS, default='front')
    parser.add_argument('--animation', choices=STATES, default='idle')
    parser.add_argument('--reduced-motion', action='store_true')
    parser.add_argument('--force-warp', action='store_true')
    args = parser.parse_args(argv)
    executable = renderer_path()
    if not executable.is_file():
        parser.error('Build the isolated renderer before starting a character preview')
    with tempfile.TemporaryDirectory(prefix='oes-eyeball-preview-') as directory:
        root = Path(directory)
        return subprocess.call(preview_command(executable, root / 'diagnostics.json',
                                               root / 'control.json', args.view,
                                               args.animation, args.reduced_motion,
                                               args.force_warp))


if __name__ == '__main__':
    raise SystemExit(main())
