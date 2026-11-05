"""Validation boundary for Blender-authored glTF 2.0 character assets."""
import json
from pathlib import Path

REQUIRED_NODE_NAMES = {
    'body', 'iris', 'pupil', 'lens',
    *(f'aperture_blade_{index:02d}' for index in range(8)),
}


def validate_gltf(path):
    path = Path(path)
    if path.suffix.lower() != '.gltf':
        raise ValueError('Phase 1 validator requires inspectable .gltf JSON')
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('asset', {}).get('version') != '2.0':
        raise ValueError('Asset must be glTF 2.0')
    nodes = value.get('nodes')
    meshes = value.get('meshes')
    materials = value.get('materials')
    if not isinstance(nodes, list) or not isinstance(meshes, list) or not isinstance(materials, list):
        raise ValueError('Asset must contain nodes, meshes, and materials')
    names = {node.get('name') for node in nodes if isinstance(node, dict)}
    missing = REQUIRED_NODE_NAMES - names
    if missing:
        raise ValueError('Asset is missing required movable character parts')
    for buffer in value.get('buffers', []):
        uri = buffer.get('uri') if isinstance(buffer, dict) else None
        if not isinstance(uri, str) or uri.startswith(('http:', 'https:', 'data:')):
            raise ValueError('Asset buffers must be bounded local files')
        candidate = (path.parent / uri).resolve()
        if path.parent.resolve() not in candidate.parents or not candidate.is_file():
            raise ValueError('Asset buffer is missing or outside its asset directory')
    return {'nodes': len(nodes), 'meshes': len(meshes), 'materials': len(materials)}
