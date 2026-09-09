"""Verify declared source controls and report all view differences, without fidelity claims."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr import sequence, image_bridge
from enr.references import digest
from probe_enfusion_source_visibility import canonical_hash


def load_capture(folder):
    scout = json.loads((folder / 'scout.json').read_text(encoding='utf-8'))
    config = json.loads((folder / 'capture-config.json').read_text(encoding='utf-8'))
    directory = folder / 'runs' / scout['run_id']
    native = json.loads((directory / 'run.json').read_text(encoding='utf-8'))
    if Path(native['directory']).resolve() != directory.resolve():
        raise ValueError('Capture manifest points outside its retained run')
    for path, key in [(directory / 'run.json', 'capture_manifest_sha256'),
                      (directory / 'console.log', 'console_sha256'),
                      (folder / 'capture-config.json', 'config_sha256')]:
        if digest(path) != scout[key]:
            raise ValueError('Retained capture evidence changed: ' + str(path))
    validation_path = folder / 'runs' / scout['validation_run'] / 'run.json'
    validation = json.loads(validation_path.read_text(encoding='utf-8'))
    if digest(validation_path) != scout['validation_manifest_sha256']:
        raise ValueError('Validation manifest changed')
    if validation['status'] != 'succeeded' or validation['process_exit_code'] != 0 or validation['terminated_owned_process']:
        raise ValueError('Addon validation did not exit naturally')
    mutable_settings = []
    for run, run_dir in [(native, directory), (validation, validation_path.parent)]:
        for name, sha in run['addon_sha256'].items():
            current_sha = digest(run_dir / 'addon' / name)
            # private_settings() passes this initially empty file to -forceSettings.
            # Workbench writes its UI state there; it is a runtime output, not source code.
            if name == 'ENR_Workbench.ini' and sha == hashlib.sha256(b'').hexdigest():
                mutable_settings.append({'run_id': run['run_id'], 'file': name,
                                         'initial_sha256': sha, 'after_run_sha256': current_sha,
                                         'scope': 'Workbench-writable UI settings; initial empty-file hash differs from runtime output.'})
            elif current_sha != sha:
                raise ValueError('Immutable addon snapshot changed: ' + name)
    verified = sequence.verify(config, native)
    if scout['frames'] != verified['frames']:
        raise ValueError('Scout frame evidence differs')
    intervals = []
    for previous, current in zip(verified['frames'], verified['frames'][1:]):
        frames = current['camera']['world_frame'] - previous['camera']['world_frame']
        if frames != config['hold_ticks_per_sample']:
            raise ValueError('Observed inter-sample update count differs from the requested hold')
        intervals.append({'from_index': previous['index'], 'to_index': current['index'],
                          'world_updates': frames,
                          'simulation_seconds': current['camera']['simulation_seconds'] - previous['camera']['simulation_seconds']})
    arrays = []
    for frame in verified['frames']:
        with Image.open(directory / frame['file']) as image:
            if image.mode != 'RGB':
                raise ValueError('Expected unconverted RGB8 source')
            arrays.append(np.array(image))
    record = {'run_id': scout['run_id'], 'config': config, 'frames': verified['frames'],
              'capture_manifest_sha256': digest(directory / 'run.json'),
              'validation_run': scout['validation_run'], 'validation_manifest_sha256': digest(validation_path),
              'console_sha256': digest(directory / 'console.log'), 'addon_sha256': native['addon_sha256'],
              'settings_readback': verified['settings_readback'], 'environment': verified['environment'],
              'world_binding': scout['world_binding'], 'limits': verified['limits']}
    record['sample_intervals'] = intervals
    record['mutable_settings'] = mutable_settings
    return record, arrays


def difference(actual, expected):
    error = np.abs(actual.astype(np.float64) - expected.astype(np.float64))
    return {'rgb_mae_8bit': float(error.mean()), 'rgb_rmse_8bit': float(np.sqrt(np.mean(error * error))),
            'rgb_max_error_8bit': int(error.max()),
            'changed_pixel_fraction': float(np.mean(np.any(error != 0, axis=2))),
            'pixels_over_8_code_values_fraction': float(np.mean(np.any(error > 8, axis=2)))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--original-warehouse', required=True)
    parser.add_argument('--original-montignac', required=True)
    parser.add_argument('--world-inventory', required=True)
    parser.add_argument('--review', required=True, help='Explicit visual observations keyed by control directory name')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    plan_path = ROOT / 'scenes/arma-source-visibility-v1.json'
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    repeat_plan_path = ROOT / 'scenes/arma-source-visibility-repeats-v1.json'
    repeat_plan = json.loads(repeat_plan_path.read_text(encoding='utf-8'))
    review_path = Path(args.review)
    review = json.loads(review_path.read_text(encoding='utf-8'))
    roots = {'warehouse': Path(args.original_warehouse), 'montignac': Path(args.original_montignac)}
    originals, original_arrays, base_configs = {}, {}, {}
    for scene, entry in plan['scenes'].items():
        base, binding = image_bridge.load_probe_config(ROOT / entry['config'], args.world_inventory)
        if canonical_hash(base) != entry['canonical_config_sha256']:
            raise ValueError('Declared original config differs')
        record, arrays = load_capture(roots[scene])
        if record['run_id'] != entry['original_run'] or record['config'] != base or record['world_binding'] != binding:
            raise ValueError('Original capture binding differs')
        originals[scene], original_arrays[scene], base_configs[scene] = record, arrays, base
    reports, arrays_by_id = {}, {}
    for folder in sorted(Path(args.root).iterdir()):
        if not folder.is_dir():
            continue
        control = json.loads((folder / 'control.json').read_text(encoding='utf-8'))
        if control['status'] != 'captured' or control['driver_exit_code'] != 0:
            raise ValueError('Control did not complete: ' + folder.name)
        if control['plan_sha256'] != digest(plan_path):
            raise ValueError('Control used a different declared plan')
        if digest(folder / 'capture/scout.json') != control['scout_report_sha256']:
            raise ValueError('Control scout report changed')
        scene, condition = control['scene'], control['condition']
        expected = dict(base_configs[scene]); expected.update(plan['conditions'][condition])
        if control['overrides'] != plan['conditions'][condition] or control['source_config_canonical_sha256'] != canonical_hash(base_configs[scene]):
            raise ValueError('Control overrides differ')
        if control['requested_config_canonical_sha256'] != canonical_hash(expected):
            raise ValueError('Requested config differs')
        record, arrays = load_capture(folder / 'capture')
        if record['config'] != expected or record['world_binding'] != originals[scene]['world_binding']:
            raise ValueError('Actual capture config differs')
        visual = review[folder.name]
        if visual['run_id'] != record['run_id'] or len(visual['frames']) != len(arrays):
            raise ValueError('Missing visual review')
        for frame, observed in zip(record['frames'], visual['frames']):
            if observed['sha256'] != frame['sha256'] or observed['index'] != frame['index'] or not observed['observation']:
                raise ValueError('Review does not bind every frame')
        record.update(id=folder.name, scene=scene, condition=condition,
                      control_report_sha256=digest(folder / 'control.json'),
                      driver_sha256=control['driver_sha256'], visual_review=visual,
                      neural_processing=False, aligned_reference=False, live_integration=False)
        reports[folder.name], arrays_by_id[folder.name] = record, arrays
    if set(reports) != set(review):
        raise ValueError('Review/control set differs')
    expected_ids = {scene + '-' + condition for scene in plan['scenes'] for condition in plan['conditions']}
    for scene in repeat_plan['scenes']:
        for repeat in range(2, 2 + repeat_plan['additional_repeats_per_scene']):
            name = scene + '-hold-repeat' + str(repeat)
            expected_ids.add(name)
            if name not in reports or reports[name]['condition'] != repeat_plan['condition']:
                raise ValueError('A declared follow-up repeat is missing or uses a different condition')
    if set(reports) != expected_ids:
        raise ValueError('Completed controls differ from the declared initial and follow-up set')
    for scene in plan['scenes']:
        for condition in plan['conditions']:
            if scene + '-' + condition not in reports:
                raise ValueError('A declared initial condition is missing')
    for name, record in reports.items():
        scene = record['scene']; roi = plan['scenes'][scene]['inspection_roi_xyxy']
        references = {'original': original_arrays[scene], 'fresh_repeat': arrays_by_id[scene + '-repeat']}
        if record['condition'] == 'camera-hold':
            references['first_camera_hold'] = arrays_by_id[scene + '-camera-hold']
        comparisons = {}
        for label, reference in references.items():
            metrics = []
            for i, (actual, expected) in enumerate(zip(arrays_by_id[name], reference)):
                item = {'index': i, 'full_image': difference(actual, expected)}
                if i == plan['scenes'][scene]['anomaly_sample']:
                    x0, y0, x1, y1 = roi
                    item['inspection_roi_xyxy'] = roi
                    item['inspection_roi'] = difference(actual[y0:y1, x0:x1], expected[y0:y1, x0:x1])
                metrics.append(item)
            comparisons[label] = metrics
        record['comparisons'] = comparisons
    result = {'schema_version': 1, 'scope': plan['scope'], 'plan_sha256': digest(plan_path),
              'follow_up_plan': repeat_plan, 'follow_up_plan_sha256': digest(repeat_plan_path),
              'reporter_sha256': digest(__file__), 'visual_review_sha256': digest(review_path),
              'originals': originals, 'controls': list(reports.values()),
              'metric_scope': 'Unaligned RGB8 source differences. No image is a photorealistic target; errors do not score neural fidelity.',
              'integration_verified': False, 'aligned_appearance_pair_verified': False}
    # Stable report bytes across checkouts; nested run hashes retain original raw artifacts.
    output = Path(args.out); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes((json.dumps(result, indent=2, allow_nan=False) + '\n').encode('utf-8'))
    print(json.dumps([{'id': r['id'], 'run': r['run_id'], 'observations': r['visual_review']['summary']} for r in reports.values()], indent=2))


if __name__ == '__main__':
    main()
