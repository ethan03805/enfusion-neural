"""Bind successful build/load/capture controls to the original geometry reports."""
import argparse
import json
from pathlib import Path
import re
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr import sequence
from enr.references import digest


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def import_trial(root):
    root = Path(root).resolve()
    path = root / 'import.json'
    report = read(path)
    run = (root / 'runs' / report['run_id']).resolve()
    if root not in run.parents or digest(run / 'run.json') != report['run_manifest_sha256']:
        raise ValueError('Import manifest changed')
    manifest = read(run / 'run.json')
    validation_path = root / 'runs' / report['validation_run'] / 'run.json'
    validation = read(validation_path)
    if (digest(validation_path) != report['validation_manifest_sha256'] or
            validation['status'] != 'succeeded' or validation['process_exit_code'] != 0):
        raise ValueError('Native compile validation mismatch')
    if report['status'] != 'succeeded' or digest(run / 'console.log') != report['console_sha256']:
        raise ValueError('Native trial failed or log changed')
    if digest(run / 'addon/Scripts/WorkbenchGame/ENR_MaterialRoomImportPlugin.c') != report['plugin_sha256']:
        raise ValueError('Native plugin changed')
    text = (run / 'console.log').read_text(encoding='utf-8')
    events = [json.loads(line.split('ENR_IMPORT ', 1)[1]) for line in text.splitlines() if 'ENR_IMPORT ' in line]
    if events != [json.loads(s) for s in report['native_records']]:
        raise ValueError('Native events differ from summary')
    base = run / 'addon/Assets/ENR_ReferenceRoom'
    for asset in report['retained_assets']:
        candidate = (base / asset['file']).resolve()
        if base not in candidate.parents or digest(candidate) != asset['sha256']:
            raise ValueError('Imported asset changed')
    if report['route'] == 'build-live':
        if (not manifest['alive_after_build_observation'] or manifest['build_observation_seconds'] < 10
                or 'Build successful' not in text or manifest.get('error')):
            raise ValueError('Build completion was not observed while editor remained alive')
    elif manifest['process_exit_code'] != 0 or manifest['terminated_owned_process']:
        raise ValueError('Load or inspection did not exit naturally')
    if report['route'] == 'load-completed' and [e['count'] for e in events if e['event'] == 'materials'] != [7]:
        raise ValueError('Expected seven material regions')
    return {'trial': root.name, 'run_id': report['run_id'], 'operation': report['operation'],
            'route': report['route'], 'report_sha256': digest(path),
            'run_manifest_sha256': digest(run / 'run.json'), 'validation_run': report['validation_run'],
            'validation_manifest_sha256': digest(validation_path), 'plugin_sha256': report['plugin_sha256'],
            'console_sha256': report['console_sha256'], 'source_fbx_sha256': report['source_fbx_sha256'],
            'native_exit_code': manifest['process_exit_code'], 'terminated_owned_process': manifest['terminated_owned_process'],
            'alive_after_build_observation': manifest.get('alive_after_build_observation'),
            'build_observation_seconds': manifest.get('build_observation_seconds'),
            'prior_import': report.get('prior_import'), 'native_events': events,
            'metadata_records': report.get('metadata_records', []), 'retained_assets': report['retained_assets']}


def capture_trial(root):
    root = Path(root).resolve()
    path = root / 'room.json'
    report = read(path)
    run = (root / 'runs' / report['run_id']).resolve()
    if root not in run.parents or digest(run / 'run.json') != report['capture_manifest_sha256']:
        raise ValueError('Capture manifest changed')
    if digest(run / 'console.log') != report['console_sha256'] or digest(root / 'capture-config.json') != report['capture_config_sha256']:
        raise ValueError('Capture configuration or log changed')
    native = read(run / 'run.json')
    verified = sequence.verify(sequence.load_config(root / 'capture-config.json'), native)
    if verified['frames'] != report['frames']:
        raise ValueError('Capture telemetry differs')
    validation = root / 'runs' / report['validation_run'] / 'run.json'
    if digest(validation) != report['validation_manifest_sha256'] or read(validation)['process_exit_code'] != 0:
        raise ValueError('Capture addon compile differs')
    text = (run / 'console.log').read_text(encoding='utf-8')
    observations = re.findall(r'ENR_ROOM spawned origin=<([^>]+)> mins=<([^>]+)> maxs=<([^>]+)> materials=([0-9]+)', text)
    if len(observations) != 1:
        raise ValueError('Expected one room spawn')
    origin, mins, maxs, count = observations[0]
    bounds = [[float(v) for v in s.split(',')] for s in (origin, mins, maxs)]
    expected = [[2048, 1000, 2048], [-3.1, -.2, -3], [3.1, 4, 3.1]]
    if count != '7' or not np.allclose(bounds, expected, atol=1e-5, rtol=0):
        raise ValueError('Unexpected room dimensions or material count')
    return {'trial': root.name, 'run_id': report['run_id'], 'report_sha256': digest(path),
            'capture_manifest_sha256': report['capture_manifest_sha256'],
            'console_sha256': report['console_sha256'], 'validation_manifest_sha256': digest(validation),
            'source_import_report_sha256': report['source_import_report_sha256'],
            'config_sha256': report['capture_config_sha256'], 'dimensions': report['dimensions'],
            'frames': verified['frames'], 'origin': bounds[0], 'local_bounds': bounds[1:],
            'material_count': 7, 'camera_and_projection_readback_passed': True,
            'engine_geometry_bounds_passed': True, 'appearance_pair_verified': False,
            'visual_review': 'Visible walls, floor, plinth, three spheres, box and three thin posts; default white materials, sunlight and sky differ from the Cycles reference'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--imports', nargs='+', required=True)
    parser.add_argument('--captures', nargs='+', required=True)
    parser.add_argument('--geometry-checks', nargs='+', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    imports = [import_trial(p) for p in args.imports]
    captures = [capture_trial(p) for p in args.captures]
    import_hashes = {r['report_sha256'] for r in imports}
    checks = []
    for name in args.geometry_checks:
        path = Path(name)
        check = read(path)
        if (check['status'] != 'succeeded' or len(check['meshes']) != 12
                or check['max_coordinate_error_m'] > 5e-6
                or check['load_report_sha256'] not in import_hashes
                or digest(path.with_suffix('.py')) != check['script_sha256']):
            raise ValueError('Geometry check is incomplete or its script snapshot differs')
        checks.append({'report_sha256': digest(path), 'result': check})
    if any(c['source_import_report_sha256'] not in import_hashes for c in captures):
        raise ValueError('Capture is not bound to a verified separate resource load')
    result = {'schema_version': 1, 'status': 'geometry_import_verified', 'script_sha256': digest(__file__),
              'scope': 'Original-room geometry and camera correspondence; default engine appearance only',
              'imports': imports, 'captures': captures, 'vertex_checks': checks,
              'earlier_failures': 'evidence/enfusion-material-import-v1.json',
              'correction': 'Earlier rebuild probes requested Workbench.Exit before asynchronous import completion. Keeping the private editor alive produces nonempty geometry for both unchanged original and LOD0-derived FBX. A fresh project also builds successfully. Earlier empty outputs do not establish an asset-format limitation.',
              'retained_compile_failure': {'run_id': '20260909T103203-33465720c5',
                   'reason': 'Room variable conflicted with an engine type name; renamed RoomEntity before successful native validation'},
              'geometry_import_verified': True, 'aligned_appearance_pair_verified': False,
              'renderer_integration_verified': False,
              'limits': ['No matched material parameters, lighting or color transfer',
                         'TXO vertices and native entity bounds are verified; compiled-mesh quantization and shading normals/UVs have not been numerically compared',
                         'Engine screenshots establish visible geometry; they expose no depth, normals, motion vectors or supported neural output pass',
                         'No lighting-model inference, real-Arma fidelity result, motion study or complete-frame performance claim follows']}
    Path(args.out).write_bytes((json.dumps(result, indent=2, allow_nan=False) + '\n').encode('utf-8'))
    print(json.dumps({'status': result['status'], 'imports': len(imports), 'captures': len(captures), 'geometry_checks': len(checks)}))


if __name__ == '__main__':
    main()
