"""Validated local-file configuration for the native renderer tuning panel."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


SCHEMA_VERSION = 1
CONTROL_FILENAME = 'renderer-tuning.json'
DIAGNOSTICS_FILENAME = 'renderer-diagnostics.json'

# These values reproduce the accepted renderer baseline. The artwork scale of .86
# is the same fixed quad extent used by the original native proof.
CANONICAL_PARAMETERS = {
    'scale': 0.86,
    'x': 0.0,
    'y': 0.0,
    'rotation': 0.0,
    'opacity': 1.0,
    'glow_intensity': 0.0,
    'glow_radius': 0.0,
    'brightness': 1.0,
    'exposure': 0.0,
    'lighting_intensity': 1.0,
    'depth': 0.0,
    'perspective_x': 0.0,
    'perspective_y': 0.0,
    'width': 512,
    'height': 512,
}

PARAMETER_LIMITS = {
    'scale': (0.10, 1.50),
    'x': (-1.0, 1.0),
    'y': (-1.0, 1.0),
    'rotation': (-180.0, 180.0),
    'opacity': (0.0, 1.0),
    'glow_intensity': (0.0, 2.0),
    'glow_radius': (0.0, 32.0),
    'brightness': (0.25, 2.5),
    'exposure': (-2.0, 2.0),
    'lighting_intensity': (0.25, 2.5),
    'depth': (-1.0, 1.0),
    'perspective_x': (-0.5, 0.5),
    'perspective_y': (-0.5, 0.5),
    'width': (220, 1600),
    'height': (220, 1600),
}


def local_renderer_dir(env=None):
    env = os.environ if env is None else env
    root = env.get('LOCALAPPDATA')
    if not root:
        raise ValueError('Windows local application data is unavailable')
    return Path(root) / 'OES' / 'Core' / 'Renderer'


def default_paths(env=None):
    root = local_renderer_dir(env)
    return root / CONTROL_FILENAME, root / DIAGNOSTICS_FILENAME


def validate_parameters(values):
    """Return a complete bounded renderer snapshot; reject unknown fields."""
    if not isinstance(values, dict) or set(values) - set(CANONICAL_PARAMETERS):
        raise ValueError('Renderer parameters contain unsupported fields')
    result = dict(CANONICAL_PARAMETERS)
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f'{name} must be numeric')
        low, high = PARAMETER_LIMITS[name]
        if not low <= float(value) <= high:
            raise ValueError(f'{name} is outside its supported range')
        result[name] = int(value) if name in ('width', 'height') else float(value)
    return result


def read_parameters(path):
    try:
        payload = json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return dict(CANONICAL_PARAMETERS)
    except (OSError, ValueError, TypeError) as error:
        raise ValueError('Renderer parameter file is unavailable or invalid') from error
    if not isinstance(payload, dict) or payload.get('version') != SCHEMA_VERSION:
        raise ValueError('Renderer parameter schema is unsupported')
    return validate_parameters(payload.get('parameters'))


def write_parameters(path, values):
    """Atomically publish one complete snapshot so the renderer never sees a partial file."""
    path = Path(path)
    parameters = validate_parameters(values)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=path.name, suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8', newline='\n') as output:
            json.dump({'version': SCHEMA_VERSION, 'parameters': parameters}, output,
                      sort_keys=True, separators=(',', ':'))
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return parameters


def save_preset(path, values):
    return write_parameters(path, values)


def load_preset(path):
    return read_parameters(path)


def read_diagnostics(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return None
    if not isinstance(value, dict):
        return None
    allowed = {
        'status', 'adapter_name', 'feature_level', 'device_type', 'fps',
        'width', 'height', 'parameters',
    }
    return {key: value[key] for key in allowed if key in value}

