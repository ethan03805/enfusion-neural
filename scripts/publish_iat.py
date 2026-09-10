"""Publish the fixed IAT review with original artifacts and measured failures."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    target = ROOT / 'evidence/iat-evaluation-v1.json'
    if target.exists():
        raise FileExistsError(target)
    run = ROOT / 'runs/iat-evaluation-v1'
    plan_path = ROOT / 'scenes/playable-iat-evaluation-v1.json'
    source_path = ROOT / 'runs/pretrained/iat-exposure-v1/source.json'
    plan, result, source = read(plan_path), read(run / 'report.json'), read(source_path)
    selection = read(run / 'selection-decision.json')
    if result['status'] != 'completed' or selection['decision'] != 'reject' or selection['reserved_view_opened']:
        raise ValueError('Unexpected inference or selection state')
    for path, expected in [(plan_path, result['plan_sha256']), (run / 'driver.py', result['driver_sha256']),
                           (source_path, result['provenance_sha256']), (run / 'model.onnx', result['onnx_sha256']),
                           (run / result['profile_file'], result['profile_sha256'])]:
        if digest(path) != expected:
            raise ValueError('Changed evidence: ' + str(path))
    for name, row in source['files'].items():
        if digest(source_path.parent / name) != row['sha256']:
            raise ValueError('Changed author file: ' + name)
    files = []
    for index, row in enumerate(result['images']):
        native = ROOT / row['path']
        if digest(native) != row['sha256']:
            raise ValueError('Changed source')
        for name, sha in row['artifact_hashes'].items():
            if digest(run / name) != sha:
                raise ValueError('Changed retained output: ' + name)
        for kind in ('raw', 'protected'):
            if index < 2 and selection['artifacts'][f'{index}-{kind}'] != digest(run / f'{index:02d}-{kind}.png'):
                raise ValueError('Changed selection output')
        for kind, path in [('source', native), ('raw', run / f'{index:02d}-raw.png'), ('protected', run / f'{index:02d}-protected.png')]:
            name = f'iat-{row["name"]}-{kind}.png'
            if (ROOT / 'docs/media' / name).exists():
                raise FileExistsError(name)
            files.append((path, name, kind))
    closed = datetime.now(timezone.utc)
    elapsed = (closed - datetime.fromisoformat(plan['started_at'].replace('Z', '+00:00'))).total_seconds() / 60
    review = {
        'scope': 'All three complete native 2560x1440 sources, raw 960x540 outputs and protected 2560x1440 outputs inspected at original dimensions. Selection decision recorded before opening reserved outputs. No motion trial.',
        'reserved': 'The raw foliage view brightens the trunk while increasing green/cyan saturation and deepening ground and foliage shadows. Bark identity and broad boundaries remain, but the softer resized raw output does not reconstruct fine material detail. The protected version changes color slightly and exposes the hard bottom HUD-mask seam across the trunk and grass.',
        'decision': 'Reject raw and protected IAT for appearance and cost. No further precision/export, motion or live integration trial.',
        'guard_limit': 'The luminance guard permits newly clipped individual channels. Hard fixed HUD-mask edges produce visible discontinuities. Retain these diagnostic defects; the live DCE compositor uses feathered margins and is unchanged.',
        'reference_limit': 'No aligned photographic ground truth; subjective appearance review and quantitative source differences do not measure physical realism.',
        'timing_limit': '37 synchronized calls including warmups produce 1517 DirectML node execution events, not 1517 inferences. Every call reads back all three author outputs. These are not pure GPU kernel or complete game frame timings.'
    }
    report = {'schema_version': 1, 'date': '2026-09-10', 'outcome': 'rejected_appearance_visibility_and_cost',
              'evaluation_closed_at': closed.isoformat(), 'minutes_since_plan_start': elapsed,
              'within_declared_time_bound': elapsed <= plan['maximum_minutes'],
              'plan': plan, 'source': source, 'measurement': result, 'selection': selection, 'review': review,
              'working_package_changed': False, 'training_performed': False, 'photorealistic_gain_accepted': False,
              'source_hashes': {p.relative_to(ROOT).as_posix(): digest(p) for p in
                                (plan_path, source_path, run / 'report.json', run / 'selection-decision.json', Path(__file__))},
              'published_media': []}
    manifest_path = ROOT / 'docs/media/manifest.json'
    manifest = read(manifest_path)
    for path, name, kind in files:
        transform = {'source': 'Unchanged 2560x1440 gameplay PNG.',
                     'raw': 'Unchanged author output PNG, 960x540; input bilinear reduced from native 2560x1440. Float output clamped and rounded to RGB8 for display; floats retained.',
                     'protected': 'Fixed bounded residual composed at native 2560x1440; hard HUD-mask seams and final channel clipping retained. No spatial warping.'}[kind]
        entry = {'file': name, 'sha256': digest(path), 'bytes': path.stat().st_size,
                 'dimensions': list(Image.open(path).size), 'source_record': target.relative_to(ROOT).as_posix(),
                 'source_artifact': path.relative_to(ROOT).as_posix(), 'source_sha256': digest(path),
                 'transformation': transform, 'rights': 'Arma Reforger imagery © Bohemia Interactive, outside MIT license; IAT model/source Apache-2.0.'}
        report['published_media'].append(entry)
        manifest['images'].append(entry)
        shutil.copyfile(path, ROOT / 'docs/media' / name)
    write_json(target, report)
    write_json(manifest_path, manifest)
    print(json.dumps({'elapsed_minutes': elapsed, 'within_bound': report['within_declared_time_bound'], 'published_images': len(files)}))


if __name__ == '__main__':
    main()
