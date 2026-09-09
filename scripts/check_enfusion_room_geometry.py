"""Blender: compare imported TXO vertices with the hash-bound original FBX.

This verifies mesh point positions by existing vertex index before appearance
calibration. It does not verify shader normals, scene buffers or photographic truth.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True)
    parser.add_argument('--loaded-import', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    source = Path(args.source_root).resolve() / 'material-room.fbx'
    evidence_path = ROOT / 'evidence/material-room-v1.json'
    evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
    if digest(source) != evidence['source_artifacts']['fbx_sha256']:
        raise ValueError('Original geometry hash differs')
    loaded = Path(args.loaded_import).resolve()
    load_path = loaded / 'import.json'
    load = json.loads(load_path.read_text(encoding='utf-8'))
    if load['status'] != 'succeeded' or load['route'] != 'load-completed':
        raise ValueError('Require a separate successful native load')
    txo = loaded / 'runs' / load['run_id'] / 'addon/Assets/ENR_ReferenceRoom/material-room.txo'
    records = [a for a in load['retained_assets'] if a['file'] == 'material-room.txo']
    if len(records) != 1 or digest(txo) != records[0]['sha256']:
        raise ValueError('Imported TXO differs from the loaded resource record')
    text = txo.read_text(encoding='utf-8')
    meshes = {}
    for match in re.finditer(r'\$mesh "([^"]+)" \{(.*?)(?=\n  \$mesh |\Z)', text, re.S):
        name, body = match.groups()
        positions = re.search(r'\$verts \{([^}]+)\}', body)
        if not positions or name in meshes:
            raise ValueError('Missing or duplicate mesh positions')
        meshes[name] = np.array([[float(v) for v in line.split()[:3]] for line in positions[1].splitlines() if line.strip()])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    originals = {o.name: o for o in bpy.context.scene.objects if o.type == 'MESH'}
    if set(originals) != set(meshes) or len(meshes) != 12:
        raise ValueError('Imported mesh identities do not match all 12 originals')
    results = []
    for name in sorted(originals):
        original = np.array([list(originals[name].matrix_world @ v.co) for v in originals[name].data.vertices])[:, [0, 2, 1]]
        actual = meshes[name]
        if actual.shape != original.shape:
            raise ValueError('Vertex count differs for ' + name)
        error = float(np.abs(actual-original).max())
        if error > 5e-6:
            raise ValueError('Per-index geometry differs for ' + name + ': ' + str(error))
        results.append({'mesh': name, 'vertices': len(actual), 'max_coordinate_error_m': error,
                        'imported_min': actual.min(axis=0).tolist(), 'imported_max': actual.max(axis=0).tolist()})
    result = {'schema_version': 1, 'status': 'succeeded', 'operation': 'original-fbx-txo-vertex-comparison',
              'script_sha256': digest(__file__), 'blender': bpy.app.version_string,
              'original_fbx_sha256': digest(source), 'load_report_sha256': digest(load_path),
              'txo_sha256': digest(txo), 'mapping': 'Blender [x,y,z] to Enfusion [x,z,y]',
              'comparison': 'All vertex positions by existing index; no alignment fitting or reordering',
              'tolerance_m': 5e-6, 'meshes': results,
              'max_coordinate_error_m': max(r['max_coordinate_error_m'] for r in results),
              'limits': ['TXO mesh points only; compiled-mesh quantization, shading normals, UVs and raster silhouettes require separate checks',
                         'Materials, lighting and color are not matched; no accepted appearance-training pair']}
    out = Path(args.out)
    if out.exists():
        raise ValueError('Choose a new geometry report path')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix('.py').write_bytes(Path(__file__).read_bytes())
    out.write_bytes((json.dumps(result, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'status': result['status'], 'meshes': len(results), 'vertices': sum(r['vertices'] for r in results), 'max_error_m': result['max_coordinate_error_m']}))


if __name__ == '__main__':
    main()
