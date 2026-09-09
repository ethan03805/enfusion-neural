"""Verify retained native import trials and publish their limited, negative result."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--roots', nargs='+', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    trials = []
    for name in args.roots:
        root = Path(name).resolve()
        report_path = root / 'import.json'
        report = json.loads(report_path.read_text(encoding='utf-8'))
        run = root / 'runs' / report['run_id']
        if root not in run.resolve().parents:
            raise ValueError('Run path outside import project')
        manifest_path = run / 'run.json'
        if digest(manifest_path) != report['run_manifest_sha256']:
            raise ValueError('Import run manifest changed')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        validation_path = root / 'runs' / report['validation_run'] / 'run.json'
        if digest(validation_path) != report['validation_manifest_sha256']:
            raise ValueError('Validation manifest changed')
        validation = json.loads(validation_path.read_text(encoding='utf-8'))
        if validation['status'] != 'succeeded' or validation['process_exit_code'] != 0:
            raise ValueError('Native compile validation did not succeed')
        log = run / 'console.log'
        plugin = run / 'addon/Scripts/WorkbenchGame/ENR_MaterialRoomImportPlugin.c'
        if digest(log) != report['console_sha256'] or digest(plugin) != report['plugin_sha256']:
            raise ValueError('Native import log or plugin changed')
        base = run / 'addon/Assets/ENR_ReferenceRoom'
        for asset in report['retained_assets']:
            path = (base / asset['file']).resolve()
            if base.resolve() not in path.parents or digest(path) != asset['sha256']:
                raise ValueError('Retained native asset changed')
        events = [json.loads(x) for x in report['native_records']]
        counts = [e['count'] for e in events if e['event'] == 'materials']
        text = log.read_text(encoding='utf-8')
        observed = [json.loads(line.split('ENR_IMPORT ', 1)[1]) for line in text.splitlines() if 'ENR_IMPORT ' in line]
        if events != observed:
            raise ValueError('Report does not match actual native telemetry')
        source_txo = base / 'material-room.txo'
        txo_text = source_txo.read_text(encoding='utf-8') if source_txo.exists() else None
        # These specific negative controls contain just $object and header #tags.
        header_only = txo_text is not None and all(
            not line.strip() or line.strip().startswith(('$object ', '#', '}'))
            for line in txo_text.splitlines())
        trials.append({
            'trial': root.name, 'run_id': report['run_id'],
            'report_sha256': digest(report_path), 'run_manifest_sha256': digest(manifest_path),
            'validation_run': report['validation_run'], 'validation_manifest_sha256': digest(validation_path),
            'native_compile_validation_passed': True,
            'route': report.get('route', manifest.get('route', 'generic')),
            'reported_status': report['status'], 'native_exit_code': manifest['process_exit_code'],
            'terminated_by_runner': manifest['terminated_owned_process'],
            'error': manifest.get('error'), 'source_fbx_sha256': report['source_fbx_sha256'],
            'plugin_sha256': digest(plugin), 'console_sha256': digest(log),
            'retained_assets': report['retained_assets'], 'native_events': events,
            'material_counts': counts, 'txo_contains_only_header': header_only,
            'resource_load_observed': any(e['event'] == 'mesh_loaded' for e in events),
            'room_import_accepted': False, 'engine_geometry_verified': False,
            'derivation': report.get('derivation'),
        })
    if any(not t['txo_contains_only_header'] for t in trials if t['resource_load_observed']):
        raise ValueError('This negative-control summary needs review for a nonempty imported resource')
    result = {'schema_version': 1, 'status': 'import_not_verified',
              'scope': 'Original material-room FBX registration and resource-load probes only',
              'script_sha256': digest(__file__), 'trials': trials,
              'interpretation': 'Resource-load success is insufficient: completed outputs contain no TXO mesh sections; observed loads report zero materials.',
              'visual_review': 'No imported room image exists; no geometry or appearance claim is accepted',
              'engine_geometry_verified': False, 'aligned_appearance_pair_verified': False,
              'renderer_integration_verified': False}
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes((json.dumps(result, indent=2, allow_nan=False) + '\n').encode('utf-8'))
    print(json.dumps({'trials': len(trials), 'status': result['status']}))


if __name__ == '__main__':
    main()
