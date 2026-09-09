"""Blender: derive an explicitly LOD0-named FBX from the reviewed original.

No rendering, fitting, material edits or changes to the reference artifacts.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def geometry():
    result = {}
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            result[obj.name.removesuffix('_LOD0')] = {
                'vertices': [list(obj.matrix_world @ v.co) for v in obj.data.vertices],
                'polygons': [list(p.vertices) for p in obj.data.polygons],
                'material_indices': [p.material_index for p in obj.data.polygons],
                'materials': [s.material.name if s.material else None for s in obj.material_slots],
            }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    source = Path(args.source_root).resolve() / 'material-room.fbx'
    evidence_path = ROOT / 'evidence/material-room-v1.json'
    evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
    if digest(source) != evidence['source_artifacts']['fbx_sha256']:
        raise ValueError('Original reference FBX hash mismatch')
    out = Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Choose an empty derived export directory')
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    before = geometry()
    if len(before) != 12:
        raise ValueError('Expected all 12 original meshes')
    for obj in bpy.context.scene.objects:
        obj.name += '_LOD0'
    if geometry() != before:
        raise ValueError('Naming changed the in-memory geometry or material slots')
    target = out / 'material-room.fbx'
    bpy.ops.export_scene.fbx(filepath=str(target), use_selection=False, object_types={'MESH'},
                             axis_forward='-Z', axis_up='Y', add_leaf_bones=False, bake_anim=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(target))
    after = geometry()
    if set(before) != set(after):
        raise ValueError('Roundtrip changed mesh identity')
    max_delta = 0.0
    for name, original in before.items():
        returned = after[name]
        for key in ('polygons', 'material_indices', 'materials'):
            if original[key] != returned[key]:
                raise ValueError('Roundtrip changed topology or material slots: ' + name)
        if len(original['vertices']) != len(returned['vertices']):
            raise ValueError('Roundtrip changed vertex count')
        for a, b in zip(original['vertices'], returned['vertices']):
            max_delta = max(max_delta, *(abs(x-y) for x, y in zip(a, b)))
    if max_delta > 2e-6:
        raise ValueError('Roundtrip coordinate drift exceeds 2 micrometres')
    report = {'schema_version': 1, 'status': 'succeeded', 'operation': 'original-room-lod0-export',
              'blender': bpy.app.version_string, 'script_sha256': digest(__file__),
              'original_fbx_sha256': digest(source), 'source_evidence_sha256': digest(evidence_path),
              'fbx_sha256': digest(target), 'mesh_count': len(before),
              'in_memory_geometry_unchanged': True, 'topology_and_material_slots_equal': True,
              'max_roundtrip_coordinate_error_m': max_delta, 'coordinate_tolerance_m': 2e-6,
              'change': 'Append _LOD0 to each object name and re-export with the original axis settings',
              'engine_geometry_verified': False, 'aligned_appearance_pair_verified': False}
    (out / 'derivation.json').write_bytes((json.dumps(report, indent=2) + '\n').encode('utf-8'))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
