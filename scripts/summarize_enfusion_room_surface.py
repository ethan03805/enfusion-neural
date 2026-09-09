"""Verify and publish the original room's material schema and surface controls."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest
from summarize_enfusion_room_geometry import import_trial


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def surface(path, load):
    path = Path(path).resolve()
    report = read(path)
    if (report['operation'] != 'original-fbx-txo-face-corner-comparison'
            or report['script_sha256'] != digest(path.with_suffix('.py'))
            or report['load_report_sha256'] != load['report_sha256']
            or report['source_evidence_sha256'] != digest(ROOT / 'evidence/material-room-v1.json')
            or report['original_fbx_sha256'] != load['source_fbx_sha256']):
        raise ValueError('Surface provenance differs')
    txo = [r['sha256'] for r in load['retained_assets'] if r['file'] == 'material-room.txo']
    if txo != [report['txo_sha256']] or len(report['meshes']) != 12:
        raise ValueError('Expected same loaded TXO and twelve meshes')
    # These are failures, intentionally preserved rather than reclassified.
    if report['status'] != 'failed' or sorted(report['failed_meshes']) != [
            'metal-sphere', 'post-0', 'post-1', 'post-2', 'rough-sphere', 'white-sphere']:
        raise ValueError('Unexpected surface result; review before publication')
    if report['tolerances'] != {'position_m': 5e-6, 'normal_component': 2e-5, 'uv_component': 2e-6}:
        raise ValueError('Initial tolerance contract changed')
    if any(not m['topology_equal_by_vertex_index'] or m['material_mismatches'] != 0
           or m['winding']['reversed_cyclic_order'] != m['faces'] for m in report['meshes']):
        raise ValueError('Unexpected topology/material/winding mismatch')
    return {'report_sha256': digest(path), 'result': report}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schema-root', required=True)
    parser.add_argument('--loaded-import', required=True)
    parser.add_argument('--initial-surface', required=True)
    parser.add_argument('--diagnostic-surface', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists():
        raise ValueError('Choose a new evidence path')
    load = import_trial(args.loaded_import)
    schema = import_trial(args.schema_root)
    schema_root = Path(args.schema_root).resolve()
    native = read(schema_root / 'import.json')
    log = (schema_root / 'runs' / native['run_id'] / 'console.log').read_text(encoding='utf-8')
    metadata = [line.split('ENR_META_', 1)[1] for line in log.splitlines() if 'ENR_META_' in line]
    if metadata != schema['metadata_records']:
        raise ValueError('Material schema records differ from native log')
    if (schema['route'] != 'inspect-material' or schema['prior_import']['report_sha256'] != load['report_sha256']
            or schema['retained_assets'] != load['retained_assets']
            or [e['fields'] for e in schema['native_events'] if e['event'] == 'material_inspected'] != [142]):
        raise ValueError('Material inspection does not bind the unchanged loaded fixture')
    expected = ['FIELD path=material name=Color type=6 has_default=1 default=1 1 1 1',
                'VALUE path=material name=RoughnessScale read=1 value=1',
                'VALUE path=material name=MetalnessScale read=1 value=1']
    if any(line not in metadata for line in expected):
        raise ValueError('Expected material fields/readback absent')
    initial = surface(args.initial_surface, load)
    followup = surface(args.diagnostic_surface, load)
    left, right = initial['result'], followup['result']
    for before, after in zip(left['meshes'], right['meshes']):
        comparable = {k: v for k, v in after.items() if k != 'precision_diagnostics_only'}
        if before != comparable:
            raise ValueError('Follow-up changed measurements or acceptance')
    meshes = right['meshes']
    report = {'schema_version': 1, 'operation': 'original-room-surface-and-material-controls',
              'evidence_verification': 'succeeded; surface precision acceptance remains failed',
              'summarizer_sha256': digest(__file__),
              'prior_geometry_evidence_sha256': digest(ROOT / 'evidence/enfusion-room-geometry-v1.json'),
              'material_schema': schema, 'loaded_import': load,
              'surface_checks': {'initial': initial, 'decimal_precision_diagnostic': followup},
              'summary': {'meshes': len(meshes), 'vertices': sum(m['vertices'] for m in meshes),
                          'faces': sum(m['faces'] for m in meshes), 'face_corners': sum(m['corners'] for m in meshes),
                          'material_slots_equal': True, 'topology_equal_by_vertex_index': True,
                          'winding': 'All faces reverse cyclic order under the reflected axis mapping',
                          'normal_max_component_error': max(m['max_normal_component_error'] for m in meshes),
                          'normal_max_angle_degrees': max(m['max_normal_angle_degrees'] for m in meshes),
                          'uv_identity_max_error': max(m['uv_max_component_errors']['identity'] for m in meshes),
                          'uv_v_flip_max_error': max(m['uv_max_component_errors']['v_to_one_minus_v'] for m in meshes),
                          'normals_on_four_decimal_grid': all(m['precision_diagnostics_only']['max_imported_normal_off_four_decimal_grid'] == 0 for m in meshes),
                          'uvs_on_five_decimal_grid': all(m['precision_diagnostics_only']['max_imported_uv_off_five_decimal_grid'] == 0 for m in meshes),
                          'initial_thresholds_passed': False, 'thresholds_changed': False,
                          'interpretation': 'Observed decimal precision is consistent with the small differences. Source rounding is not exactly identical for sphere tie cases; compiled XOB precision has not been measured.'},
              'verified': {'material_container_schema': True, 'face_topology_and_named_slots': True,
                           'compiled_mesh_shading': False, 'material_parameter_mapping': False,
                           'aligned_appearance_pair': False, 'renderer_integration': False},
              'next_acceptance': [
                  'Test original material colors and packed-map conventions in new isolated captures, preserving the white-material control',
                  'Use an asymmetric texture and controlled light to verify raster orientation, material response and silhouettes',
                  'Verify color/exposure/light correspondence before accepting an engine/reference appearance pair',
                  'Resolve the supported scene-buffer and output-composition route separately'],
              'scope': 'Read-only native material schema plus offline FBX/TXO surface checks; no new capture, model fitting, game asset extraction or performance measurement'}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes((json.dumps(report, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'evidence_verification': report['evidence_verification'], 'summary': report['summary']}))


if __name__ == '__main__':
    main()
