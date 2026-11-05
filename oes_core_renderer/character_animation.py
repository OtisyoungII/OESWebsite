"""Deterministic renderer-neutral character animation contract."""
from dataclasses import dataclass
from math import fmod, sin

STATES = ('idle', 'blink', 'focus', 'scan')


@dataclass(frozen=True)
class CharacterPose:
    hover_y: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    gaze_x: float = 0.0
    gaze_y: float = 0.0
    aperture: float = 1.0
    pupil_scale: float = 1.0
    lens_depth: float = 0.0
    scan: float = 0.0


def _smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def sample_pose(state, seconds, reduced_motion=False):
    if state not in STATES:
        raise ValueError('Unsupported character animation state')
    if seconds < 0:
        raise ValueError('Animation time must be non-negative')
    if reduced_motion:
        return CharacterPose()
    values = {
        'hover_y': sin(seconds * .72) * .035,
        'pitch': sin(seconds * .31) * .018,
        'yaw': sin(seconds * .23 + .7) * .035,
        'gaze_x': sin(seconds * .41) * .055,
        'gaze_y': sin(seconds * .29 + 1.1) * .035,
    }
    if state == 'blink':
        phase = fmod(seconds + 1.9, 2.8)
        close = (_smoothstep(phase / .22) if phase < .22 else
                 1.0 - _smoothstep((phase - .22) / .26) if phase < .48 else 0.0)
        values['aperture'] = 1.0 - close * .88
    elif state == 'focus':
        focus = .5 + .5 * sin(seconds * 1.35)
        values['pupil_scale'] = .82 + focus * .23
        values['lens_depth'] = (focus - .5) * .075
    elif state == 'scan':
        phase = fmod(seconds, 3.5)
        scan = .5 + .5 * sin(phase / 1.2 * 6.2831853) if phase < 1.2 else .5
        values.update(scan=scan, gaze_x=(scan - .5) * .22,
                      gaze_y=sin(phase / 1.2 * 12.566371) * .025 if phase < 1.2 else 0)
    return CharacterPose(**values)
