"""Strict local metadata for renderer character themes."""
import json
from pathlib import Path

THEME_IDS = ('default', 'pirate-minimal', 'pirate-full')
THEME_FIELDS = {'version', 'id', 'label', 'status', 'base_character',
                'material_variant', 'accessories', 'animation_variant'}


def load_theme(path):
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(value, dict) or set(value) != THEME_FIELDS:
        raise ValueError('Invalid theme schema')
    if value['version'] != 1 or value['id'] not in THEME_IDS:
        raise ValueError('Invalid theme identity')
    if value['status'] not in ('complete', 'reserved'):
        raise ValueError('Invalid theme status')
    for key in ('label', 'base_character', 'material_variant', 'animation_variant'):
        if not isinstance(value[key], str) or not value[key]:
            raise ValueError('Invalid theme metadata')
    if not isinstance(value['accessories'], list) or not all(
            isinstance(item, str) and item for item in value['accessories']):
        raise ValueError('Invalid theme accessories')
    if value['id'] != 'default' and value['status'] != 'reserved':
        raise ValueError('Placeholder theme cannot be marked complete')
    return value
