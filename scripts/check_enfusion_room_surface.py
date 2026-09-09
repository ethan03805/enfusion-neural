"""Blender: compare original FBX face corners with a hash-bound Enfusion TXO.

Checks topology, material slots, axis-mapped normals and two explicit UV
conventions. It does not inspect compiled XOB data or renderer buffers.
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
TOLERANCES = {'position_m': 5e-6, 'normal_component': 2e-5, 'uv_component': 2e-6}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def block(text, token):
    match = re.search(re.escape(token) + r'\s*\{', text)
    if not match:
        raise ValueError('Missing block: ' + token)
    depth = 1
    for end in range(match.end(), len(text)):
        depth += (text[end] == '{') - (text[end] == '}')
        if depth == 0:
            return text[match.end():end]
    raise ValueError('Unclosed block: ' + token)


def rows(text, token, dtype, columns=None):
    result = [[dtype(v) for v in line.split()] for line in block(text, token).splitlines() if line.strip()]
    if not result or (columns is not None and any(len(r) != columns for r in result)):
        raise ValueError('Empty or malformed rows: ' + token)
    if dtype is float and not np.isfinite(np.asarray(result)).all():
        raise ValueError('Non-finite data: ' + token)
    return result


def cyclic_equal(first, second):
    return any(first == second[n:] + second[:n] for n in range(len(second)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True)
    parser.add_argument('--loaded-import', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    out = Path(args.out).resolve()
    if out.exists() or out.with_suffix('.py').exists():
        raise ValueError('Choose a new report and script snapshot path')
    source = Path(args.source_root).resolve() / 'material-room.fbx'
    evidence_path = ROOT / 'evidence/material-room-v1.json'
    evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
    if digest(source) != evidence['source_artifacts']['fbx_sha256']:
        raise ValueError('Original FBX hash differs')
    loaded = Path(args.loaded_import).resolve()
    load_path = loaded / 'import.json'
    load = json.loads(load_path.read_text(encoding='utf-8'))
    if load['status'] != 'succeeded' or load['route'] != 'load-completed':
        raise ValueError('Require a separate successful native load')
    run = (loaded / 'runs' / load['run_id']).resolve()
    if loaded not in run.parents or digest(run / 'run.json') != load['run_manifest_sha256']:
        raise ValueError('Native load run path or manifest differs')
    manifest = json.loads((run / 'run.json').read_text(encoding='utf-8'))
    if manifest['process_exit_code'] != 0 or manifest['terminated_owned_process']:
        raise ValueError('Native load did not exit naturally')
    if digest(run / 'console.log') != load['console_sha256']:
        raise ValueError('Native load log differs')
    txo = run / 'addon/Assets/ENR_ReferenceRoom/material-room.txo'
    records = [a for a in load['retained_assets'] if a['file'] == 'material-room.txo']
    if len(records) != 1 or digest(txo) != records[0]['sha256']:
        raise ValueError('TXO differs from native load record')
    text = txo.read_text(encoding='utf-8')
    materials = re.findall(r'\$material "([^"]+)"', block(text, '$materials'))
    if len(materials) != 7 or len(set(materials)) != 7:
        raise ValueError('Expected seven unique global material names')
    names = re.findall(r'\$mesh "([^"]+)"\s*\{', text)
    if len(names) != 12 or len(set(names)) != 12:
        raise ValueError('Expected twelve unique mesh names')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(source))
    originals = {o.name: o for o in bpy.context.scene.objects if o.type == 'MESH'}
    if set(originals) != set(names):
        raise ValueError('Original mesh identities differ')
    results = []
    failures = []
    for name in sorted(names):
        body = block(text, '$mesh "' + name + '"')
        verts = np.asarray(rows(body, '$verts', float, 4))[:, :3]
        normals = np.asarray(rows(body, '$normals', float, 3))
        uvs = np.asarray(rows(body, '$texCoords', float, 2))
        corners = rows(body, '$faceVerts', int, 3)
        faces = rows(body, '$faces', int)
        obj = originals[name]
        mesh = obj.data
        original_positions = np.asarray([list(obj.matrix_world @ v.co) for v in mesh.vertices])[:, [0, 2, 1]]
        if verts.shape != original_positions.shape:
            raise ValueError('Vertex count differs: ' + name)
        position_error = float(np.abs(verts - original_positions).max())
        original_faces = {}
        for polygon in mesh.polygons:
            key = tuple(sorted(polygon.vertices))
            if key in original_faces or len(set(key)) != len(key):
                raise ValueError('Duplicate/degenerate source face: ' + name)
            original_faces[key] = polygon
        if mesh.uv_layers.active is None:
            raise ValueError('Source has no active UV map: ' + name)
        source_normals, actual_normals, source_uvs, actual_uvs = [], [], [], []
        orientation = {'same_cyclic_order': 0, 'reversed_cyclic_order': 0, 'other': 0}
        material_mismatches = 0
        used_faces, used_corners = set(), set()
        normal_transform = obj.matrix_world.to_3x3().inverted().transposed()
        for face in faces:
            mat, count, *indices = face
            if count != len(indices) or count < 3 or not 0 <= mat < len(materials):
                raise ValueError('Malformed imported face: ' + name)
            if any(i < 0 or i >= len(corners) or i in used_corners for i in indices):
                raise ValueError('Invalid or reused face corner: ' + name)
            used_corners.update(indices)
            entries = [corners[i] for i in indices]
            order = [c[0] for c in entries]
            key = tuple(sorted(order))
            if key not in original_faces or key in used_faces:
                raise ValueError('Changed or duplicate topology: ' + name)
            used_faces.add(key)
            polygon = original_faces[key]
            source_order = list(polygon.vertices)
            orientation['same_cyclic_order' if cyclic_equal(order, source_order) else
                        'reversed_cyclic_order' if cyclic_equal(order, source_order[::-1]) else 'other'] += 1
            material_mismatches += (materials[mat] != mesh.materials[polygon.material_index].name)
            loop_by_vertex = {mesh.loops[i].vertex_index: i for i in polygon.loop_indices}
            for vertex, normal_index, uv_index in entries:
                if not (0 <= normal_index < len(normals) and 0 <= uv_index < len(uvs)):
                    raise ValueError('Invalid surface index: ' + name)
                loop_index = loop_by_vertex[vertex]
                normal = (normal_transform @ mesh.corner_normals[loop_index].vector).normalized()
                source_normals.append([normal.x, normal.z, normal.y])
                actual_normals.append(normals[normal_index])
                source_uvs.append(list(mesh.uv_layers.active.data[loop_index].uv))
                actual_uvs.append(uvs[uv_index])
        if len(used_faces) != len(original_faces) or len(used_corners) != len(corners):
            raise ValueError('Missing source faces or unused imported corners: ' + name)
        sn, an = np.asarray(source_normals), np.asarray(actual_normals)
        su, au = np.asarray(source_uvs), np.asarray(actual_uvs)
        normal_error = float(np.abs(sn-an).max())
        normal_lengths = np.linalg.norm(an, axis=1)
        if np.any(normal_lengths == 0):
            raise ValueError('Zero imported normal: ' + name)
        dot = np.sum(sn * an, axis=1) / (np.linalg.norm(sn, axis=1) * normal_lengths)
        angle = float(np.degrees(np.arccos(np.clip(dot, -1, 1))).max())
        flipped = su.copy()
        flipped[:, 1] = 1 - flipped[:, 1]
        uv_errors = {'identity': float(np.abs(su-au).max()), 'v_to_one_minus_v': float(np.abs(flipped-au).max())}
        uv_matches = [key for key, error in uv_errors.items() if error <= TOLERANCES['uv_component']]
        passed = (position_error <= TOLERANCES['position_m'] and normal_error <= TOLERANCES['normal_component']
                  and len(uv_matches) == 1 and material_mismatches == 0 and orientation['other'] == 0
                  and min(orientation['same_cyclic_order'], orientation['reversed_cyclic_order']) == 0)
        if not passed:
            failures.append(name)
        results.append({'mesh': name, 'passed': passed, 'vertices': len(verts), 'faces': len(faces), 'corners': len(corners),
                        'topology_equal_by_vertex_index': True, 'material_mismatches': material_mismatches,
                        'winding': orientation, 'max_position_error_m': position_error,
                        'max_normal_component_error': normal_error, 'max_normal_angle_degrees': angle,
                        'max_imported_normal_length_error': float(np.abs(normal_lengths-1).max()),
                        'precision_diagnostics_only': {
                            'max_imported_normal_off_four_decimal_grid': float(np.abs(an-np.round(an, 4)).max()),
                            'max_imported_normal_minus_source_rounded_four_decimals': float(np.abs(an-np.round(sn, 4)).max()),
                            'max_imported_uv_off_five_decimal_grid': float(np.abs(au-np.round(au, 5)).max()),
                            'max_imported_uv_minus_flipped_source_rounded_five_decimals': float(np.abs(au-np.round(flipped, 5)).max()),
                            'note': 'Added after the initial failed check to test decimal serialization; does not change acceptance tolerances'},
                        'uv_max_component_errors': uv_errors, 'matching_fixed_uv_conventions': uv_matches})
    global_uvs = set.intersection(*(set(r['matching_fixed_uv_conventions']) for r in results))
    global_winding = [k for k in ('same_cyclic_order', 'reversed_cyclic_order') if all(r['winding'][k] == r['faces'] for r in results)]
    passed = not failures and len(global_uvs) == 1 and len(global_winding) == 1
    result = {'schema_version': 1, 'status': 'succeeded' if passed else 'failed',
              'operation': 'original-fbx-txo-face-corner-comparison', 'blender': bpy.app.version_string,
              'script_sha256': digest(__file__), 'source_evidence_sha256': digest(evidence_path),
              'original_fbx_sha256': digest(source), 'load_report_sha256': digest(load_path), 'txo_sha256': digest(txo),
              'position_and_normal_mapping': 'Blender [x,y,z] to Enfusion [x,z,y]; inverse-transpose world normal transform',
              'comparison': 'Exact face vertex identities, cyclic orders and named material slots; face/corner order may differ. No fitted alignment.',
              'uv_candidates_declared_before_execution': ['identity', 'v_to_one_minus_v'],
              'matching_uv_convention_all_meshes': sorted(global_uvs), 'winding_all_meshes': global_winding,
              'tolerances': TOLERANCES, 'failed_meshes': failures, 'materials': materials, 'meshes': results,
              'limits': ['TXO intermediary only; compiled XOB normals, UVs, tangents and raster silhouettes are unverified',
                         'Matching material assignments do not verify material parameter semantics or rendered appearance',
                         'A fixed numerical UV relationship does not verify texture sampling orientation',
                         'No appearance-training pair, engine scene-buffer access, neural integration or performance claim']}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix('.py').write_bytes(Path(__file__).read_bytes())
    out.write_bytes((json.dumps(result, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'status': result['status'], 'meshes': len(results), 'faces': sum(r['faces'] for r in results),
                      'corners': sum(r['corners'] for r in results), 'uv': sorted(global_uvs),
                      'normal_max_component_error': max(r['max_normal_component_error'] for r in results), 'failures': failures}))
    if not passed:
        raise RuntimeError('Surface comparison failed; report retained')


if __name__ == '__main__':
    main()
