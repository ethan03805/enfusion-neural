"""Publish the bounded depth diagnostic, retained costs and reviewed media."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    target = ROOT / 'evidence/depth-motion-v1.json'
    if target.exists():
        raise FileExistsError(target)
    run = ROOT / 'runs/depth-motion-v1'
    review_run = ROOT / 'runs/depth-motion-review-v1'
    plan_path = ROOT / 'scenes/playable-depth-motion-v1.json'
    provenance_path = ROOT / 'runs/pretrained/depth-anything-v2-small-v1/source.json'
    plan, measurement, review = read(plan_path), read(run / 'report.json'), read(review_run / 'report.json')
    checks = [
        (plan_path, measurement['plan_sha256']),
        (provenance_path, measurement['provenance_sha256']),
        (ROOT / plan['source'], plan['source_sha256']),
        (run / 'report.json', review['parent_report_sha256']),
        (run / 'driver.py', measurement['driver_sha256']),
        (ROOT / 'scripts/evaluate_depth_motion.py', measurement['driver_sha256']),
        (ROOT / 'scripts/review_depth_motion.py', review['driver_sha256']),
        (run / 'model.onnx', measurement['onnx_sha256']),
        (run / 'predictions.npy', measurement['predictions_sha256']),
        (run / 'first-input.npy', measurement['first_input_sha256']),
        (run / 'first-cpu.npy', measurement['first_cpu_sha256']),
        (run / 'source-probe.json', measurement['source_probe_sha256']),
        (run / measurement['profile_file'], measurement['profile_sha256']),
        (review_run / 'comparison.mp4', review['video_sha256']),
    ]
    checks += [(review_run / row['path'], row['sha256']) for row in review['contact_sheets']]
    for path, expected in checks:
        if digest(path) != expected:
            raise ValueError('Changed retained artifact: ' + str(path))
    if measurement['status'] != 'inference_completed' or review['status'] != 'completed':
        raise ValueError('Incomplete result')
    if not measurement['parity']['passed'] or measurement['profile_provider_events'] != {'DmlExecutionProvider': 605}:
        raise ValueError('Unexpected parity/provider result')
    if measurement['provisional_cost_pass'] or not all(v['numeric_limits_pass'] for v in measurement['diagnostics'].values()):
        raise ValueError('Unexpected retained decision gates')
    rows = measurement['frames']
    if len(rows) != 600 or measurement['tensor_shape'] != [1, 3, 252, 448]:
        raise ValueError('Unexpected frame count/input shape')
    probe = read(review_run / 'probe.json')
    output_pts = np.array([float(f['best_effort_timestamp_time']) for f in probe['frames']])
    input_pts = np.array([r['relative_pts_s'] for r in rows])
    if len(output_pts) != 600 or np.max(np.abs(output_pts-input_pts)) > 1/15360 or not np.all(np.diff(output_pts) > 0):
        raise ValueError('Timestamp mismatch')
    keys = []
    for index in measurement['key_indices']:
        for kind in ('source', 'depth'):
            path = run / f'key-{index:04d}-{kind}.png'
            if Image.open(path).size != (2560, 1440):
                raise ValueError('Unexpected key dimensions')
            keys.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(path),
                         'index': index, 'kind': kind, 'reviewed_at_original_size': True})
    # Bind the complete reviewed contact sequence to its exact rendered frames.
    rendered_frames = [{'index': i, 'sha256': digest(run / 'frames' / f'{i:04d}.png')} for i in range(600)]
    image_files = [(ROOT / k['path'], f'depth-motion-{k["index"]:04d}-{k["kind"]}.png')
                   for k in keys if k['index'] in (0, 599)]
    video_file = (review_run / 'comparison.mp4', 'depth-motion-unretimed.mp4')
    for _, name in image_files + [video_file]:
        if (ROOT / 'docs/media' / name).exists():
            raise FileExistsError(name)
    finished = datetime.now(timezone.utc)
    elapsed = (finished-datetime.fromisoformat(plan['started_at'].replace('Z', '+00:00'))).total_seconds()/60
    report = {
        'schema_version': 1, 'date': '2026-09-10',
        'outcome': 'coarse_motion_diagnostic_passes_live_surface_lighting_unaccepted',
        'evaluation_closed_at': finished.isoformat(), 'minutes_since_plan_start': elapsed,
        'within_declared_time_bound': elapsed <= plan['maximum_minutes'],
        'plan': plan, 'source': read(provenance_path),
        'measurement': {k: v for k, v in measurement.items() if k not in ('decoder_command', 'traceback')},
        'encoding': {k: v for k, v in review.items() if k != 'encode_command'},
        'review': {
            'scope': 'All twelve chronological contact sheets covering 600 frames inspected at original 2240x1440 sheet size (224x126 per RGB/depth panel); all eight key PNGs inspected at native 2560x1440. Real-time playback inspection was not completed.',
            'plan_deviation': 'The planned entire-clip 1x playback review remains unfulfilled. Exhaustive thumbnails and four native-size key pairs do not establish full temporal or thin-feature acceptance.',
            'geometry': 'Walking and camera turning are present. Broad road gradients, building massing, near poles and trunks persist. Windows and door recesses flatten into walls; roof fittings, antennas, foliage gaps and thin railing depth remain incomplete or softened.',
            'hud': 'Small corner HUD text and the crosshair do not create an obvious large foreground shape in the reviewed maps. A small inspection prompt appears at the end. Large weapons, menus, scopes and semantic HUD protection remain untested.',
            'range': 'The visualization uses the first prediction range for all frames. Broad-plane gray levels change, including expected camera-relative depth changes; this is not a pure flicker measurement. No per-frame fit or reserved-segment tuning.',
            'decision': 'Retain this as a coarse offline depth diagnostic only. The 15.885 ms p95 model call fails the provisional 15 ms limit, and 30.162 ms median CPU preprocessing makes this Python workflow unsuitable for the live target. No normals, per-pixel relighting or live integration accepted.',
            'unknown': 'No appearance gain, complete game performance, live latency, peak GPU memory, physical input or broad environment/HUD acceptance measured by this test.'
        },
        'reviewed_keys': keys, 'rendered_frames': rendered_frames,
        'source_hashes': {p.relative_to(ROOT).as_posix(): digest(p) for p, _ in checks},
        'retained_review_report_sha256': digest(review_run / 'report.json'),
        'output_probe_sha256': digest(review_run / 'probe.json'),
        'working_package_changed': False, 'new_training_performed': False,
    }
    write_json(target, report)
    manifest_path = ROOT / 'docs/media/manifest.json'
    manifest = read(manifest_path)
    rights = 'Arma Reforger source imagery © Bohemia Interactive, outside MIT license; Depth Anything V2 Small author model Apache-2.0'
    for path, name in image_files + [video_file]:
        destination = ROOT / 'docs/media' / name
        shutil.copyfile(path, destination)
        video = name.endswith('.mp4')
        transform = review['transformation'] if video else (
            'Decoded 2560x1440 source RGB, lossless PNG.' if name.endswith('source.png') else
            '448x252 relative depth bilinear resized to 2560x1440 with align_corners=True; fixed first-frame [0,7.2019758224487305] grayscale range, visualization-only clamp, PNG. No metric scale.')
        entry = {'file': name, 'sha256': digest(destination), 'bytes': destination.stat().st_size,
                 'dimensions': [1792, 536] if video else [2560, 1440],
                 'source_record': target.relative_to(ROOT).as_posix(),
                 'source_artifact': path.relative_to(ROOT).as_posix(), 'source_sha256': digest(path),
                 'transformation': transform, 'rights': rights}
        if video:
            entry.update(duration_seconds=10, playback_speed=1, retimed=False)
        manifest['videos' if video else 'images'].append(entry)
    write_json(manifest_path, manifest)
    print(json.dumps({'published_images': len(image_files), 'published_videos': 1,
                      'within_time_bound': report['within_declared_time_bound'], 'elapsed_minutes': elapsed}))


if __name__ == '__main__':
    main()
