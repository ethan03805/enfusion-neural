"""Publish the reviewed street comparison while retaining failed route evidence.

Requires the declared local gameplay, survey, validation and review artifacts.
This publishes one measured record; it does not launch or select new runs.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def hashes(paths):
    return {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in paths}


def main():
    record = 'evidence/playable-street-v1.json'
    if (ROOT / record).exists():
        raise FileExistsError(record)
    comparison = read('runs/foliage-walk-comparison-v1.json')
    if not comparison['all_motion_and_repeat_gates_pass'] or len(comparison['runs']) != 3:
        raise ValueError('Missing accepted comparison triple')
    expected = [('standard', 'off'), ('combined', 'off'), ('combined', 'neural')]
    for row, settings in zip(comparison['runs'], expected):
        m = row['measurement']
        if (m['preset'], m['mode']) != settings or not m['recording']:
            raise ValueError('Wrong recorded configuration')
        launch = read('runs/' + row['run'] + '/launch.json')
        row['processing_hashes'] = launch['processing_hashes']
        row['addon_hashes'] = launch['addon_hashes']
    plan = ROOT / 'scenes/playable-foliage-route-v3.json'
    if sha(plan) != comparison['plan_sha256']:
        raise ValueError('Route plan changed after measurement')
    run = ROOT / 'runs/foliage-walk-comparison-web-v1'
    composed = json.loads((run / 'manifest.json').read_text())
    video = run / 'comparison.mp4'
    if sha(video) != composed['output_sha256'] or video.stat().st_size >= 100 * 1024 * 1024:
        raise ValueError('Video hash or size invalid')
    for source, digest in composed['sources'].items():
        if sha(ROOT / source) != digest:
            raise ValueError('Recorded input changed')
    probe = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'stream=width,height,duration,nb_frames', '-show_entries', 'format=duration',
        '-of', 'json', str(video)]))
    if abs(float(probe['format']['duration']) - 34) > .04:
        raise ValueError('Elapsed duration changed')
    composed['probe'] = probe
    timestamps = read('runs/foliage-walk-pilot-review-v3/timestamps.json') + read('runs/foliage-walk-comparison-review-v1/timestamps.json')
    if any(r['nonpositive_intervals'] for r in timestamps):
        raise ValueError('Source timestamps are not monotonic')
    retained = []
    for name in ['foliage-walk-pilot-v1', 'foliage-walk-pilot-v2']:
        root = ROOT / 'runs' / name
        files = [root / 'launch.json']
        files += list(root.glob('profile/logs/*/*.log'))
        files += list(root.glob('profile/logs/*/*.mdmp'))
        files += list(root.glob('route-check.json'))
        retained.append({'run': name, 'hashes': hashes(files)})
    validation_roots = [
        ROOT / 'runs/foliage-walk-validation-v1/runs/20260910T064536-60d77536e8',
        ROOT / 'runs/foliage-walk-validation-v2/runs/20260910T065524-e855ce5ffd',
        ROOT / 'runs/foliage-route-survey-v1/runs/20260910T064958-914bb557ea']
    validation = []
    for root in validation_roots:
        manifest = json.loads((root / 'run.json').read_text())
        if manifest['status'] != 'succeeded' or manifest['process_exit_code'] != 0:
            raise ValueError('Addon validation did not finish naturally')
        validation.append({'run': str(root.relative_to(ROOT)).replace('\\', '/'),
                           'hashes': hashes([root / 'run.json', root / 'console.log']),
                           'status': manifest['status'], 'process_exit_code': manifest['process_exit_code']})
    surveys = []
    for row in json.loads(plan.read_text())['surveys']:
        root = ROOT / row['run']
        if sha(root / 'frame.png') != row['image_sha256']:
            raise ValueError('Survey image changed')
        surveys.append({'run': row['run'], 'dimensions': list(Image.open(root / 'frame.png').size),
                        'hashes': hashes([root / 'run.json', root / 'frame.png', root / 'console.log'])})
    comparison.update({
        'date': '2026-09-10',
        'environment': {'game': 'Arma Reforger 1.8.0.13 Steam', 'adapter': 'AMD Radeon RX 7800 XT',
                        'input_output_dimensions': [2560, 1440], 'network_dimensions': [320, 180],
                        'model': 'Zero-DCE++ Epoch99, bounded luminance composition at strength 0.35', 'precision': 'FP32'},
        'selection': 'Second spatial candidate, first complete standard pass and first reduced/neural passes. The earlier east-facing candidate collided; the first street launch crashed before gameplay. No performance-based replacement or video retiming.',
        'coverage': 'About 74 metres on a tree-lined Saint-Philippe street, with rooflines, doors/windows, poles, guardrails, trunks and vegetation edges. This is not dense-forest traversal, combat visibility or physical-input acceptance.',
        'review': 'Full source frames at 2, 10, 20 and 30 seconds in all three recordings were inspected. The route remains passable. Neural output modestly lifts surfaces; no substantial material/lighting gain is accepted. Fine roof/leaf aliasing remains visible and is also present in the reduced source. Separate passes are not pixel-aligned.',
        'failure_explanation': 'The east-facing backyard pilot moves only 9.26m and stalls at a fence. The first street launch crashes during world loading before player/companion/recording; cause unknown, logs and dump retained. Identical retry completes. The accepted standard pass contains a 295.11ms application-present stall about 8.11s into the measurement window and a 283.33ms video timestamp gap at 9.666667–9.95s; both remain in the full recording and metrics.',
        'source_timestamps': timestamps, 'video': composed,
        'retained_failures': retained, 'addon_validation': validation,
        'route_surveys': surveys,
        'source_hashes': hashes([plan, ROOT / 'scenes/playable-foliage-route-v2.json',
                                 ROOT / 'scripts/check_foliage_route.py',
                                 ROOT / 'scripts/benchmark_playable.py',
                                 ROOT / 'scripts/launch_playable.py',
                                 ROOT / 'scripts/compose_playable_video.py']),
        'limits': 'Single recorded pass per configuration; recording costs CPU readback/conversion and AMD encoding. Whole-application Present cadence is not displayed-frame cadence. Signed capture-to-Present age is not physical input latency. No neural quality or temporal acceptance follows from passing a camera-route gate.'})
    media = ROOT / 'docs/media'
    manifest = read('docs/media/manifest.json')
    additions = []
    for source, name, is_video in [(video, 'playable-street-unretimed.mp4', True),
                                    (run / 'poster.png', 'playable-street-poster.png', False)]:
        target = media / name
        if target.exists():
            raise FileExistsError(target)
        if not is_video:
            with Image.open(source) as im:
                if im.size != (3840, 760):
                    raise ValueError('Unexpected poster dimensions')
        entry = {'file': name, 'sha256': sha(source), 'bytes': source.stat().st_size,
                 'dimensions': [3840, 760], 'source_record': record,
                 'source_artifact': str(source.relative_to(ROOT)).replace('\\', '/'),
                 'source_sha256': sha(source),
                 'transformation': composed['transformation'] if is_video else 'Lossless PNG of the comparison at 10 seconds',
                 'rights': 'Arma Reforger game imagery © Bohemia Interactive; outside MIT code license'}
        if is_video:
            entry.update(duration_seconds=34, playback_speed=1, retimed=False)
        additions.append((source, target, entry, is_video))
    for source, target, entry, is_video in additions:
        shutil.copyfile(source, target)
        manifest['videos' if is_video else 'images'].append(entry)
    (ROOT / record).write_text(json.dumps(comparison, indent=2), encoding='utf-8')
    manifest['selection'] += ' Street comparison: first complete standard/reduced/neural passes after a predeclared passability gate; original stalls and all 34 seconds retained.'
    (media / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Published reviewed street comparison with route gates, all timings and retained failure hashes.')


if __name__ == '__main__':
    main()
