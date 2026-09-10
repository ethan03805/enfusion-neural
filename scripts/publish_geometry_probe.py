"""Publish the closed bounded geometry diagnostic and reviewed native views."""
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
    target = ROOT / 'evidence/playable-geometry-probe-v1.json'
    if target.exists(): raise FileExistsError(target)
    project = ROOT / 'runs/playable-geometry-probe-v1'
    runs = sorted(p for p in (project / 'runs').iterdir() if (p / 'run.json').exists())
    manifests = [read(p / 'run.json') for p in runs]
    if [r['status'] for r in manifests] != ['failed', 'succeeded', 'succeeded', 'succeeded', 'succeeded']:
        raise ValueError('Unexpected run history')
    if [r['command'] for r in manifests].count('validate') != 3 or [r['command'] for r in manifests].count('capture') != 2:
        raise ValueError('Attempt bound changed')
    reports = [read(ROOT / f'runs/geometry-analysis-{view}-v2/report.json') for view in ['closeup', 'street']]
    for report in reports:
        for name, sha in report['source_hashes'].items():
            if digest(ROOT / name) != sha: raise ValueError('Analysis source changed')
    if reports[0]['modes'][0]['reprojection_error_pixels']['passes'] or not reports[1]['modes'][0]['reprojection_error_pixels']['passes']:
        raise ValueError('Expected initial projection failure and integer-pixel control')
    sources = [ROOT / 'scenes/playable-geometry-probe-v1.json', ROOT / 'scenes/playable-geometry-probe-v1-amendment.json', project / 'setup.json']
    for run in runs:
        sources.extend([run / 'run.json', run / 'console.log', run / 'addon/Scripts/Game/ENR_GeometryProbe.c', run / 'addon/Scripts/Game/ELab_GameCapture.c'])
    files = []
    for view, report in zip(['closeup', 'street'], reports):
        analysis = ROOT / f'runs/geometry-analysis-{view}-v2'
        sources.append(analysis / 'report.json')
        for mode in range(2):
            if digest(analysis / f'mode-{mode}.npy') != report['modes'][mode]['arrays_sha256']: raise ValueError('Ray data changed')
        files.extend([(project / 'runs' / report['run'] / 'frame.png', f'geometry-{view}-source.png', 'Unchanged native 1199x658 Workbench screenshot after the probe; no neural processing'),
            (analysis / 'mode-1-normals.png', f'geometry-{view}-normals.png', report['map_encoding'] + ' Mode 1 includes VISIBILITY; gray hits have zero normal. Schematic grid proportions; not a pixel-aligned full-resolution buffer.')])
    report = {'schema_version': 1, 'date': '2026-09-10', 'outcome': 'offline_geometry_observed_live_input_rejected',
        'plan': read(sources[0]), 'amendment': read(sources[1]),
        'investigation': {'started_at': '2026-09-10T08:30:15Z', 'last_engine_run_finished_at': manifests[-1]['finished_at'],
            'validation_attempts': 3, 'captures': 2, 'no_further_engine_attempts': True,
            'initial_compile_failure': "Variable name Material is already used as type name; renamed HitMaterial before second validation.",
            'retained_run_summaries': [{k: r.get(k) for k in ['run_id', 'command', 'status', 'wall_seconds', 'process_exit_code', 'terminated_owned_process', 'addon_sha256']} for r in manifests]},
        'views': reports,
        'review': {'inspected': 'Both complete native RGB captures, both mode normal maps in both views, and mode-0 depth maps in both views.',
            'useful': 'Broad roof, facade, road and foreground-pole orientation/depth structure is recognizable. Mode 0 has unit-length normals for all hits in these samples.',
            'limits': '64x36 sampling loses thin gutters, antennae, window/door recess detail and foliage gaps. Roof steps are coarse grid sampling. Broad foliage proxies do not reproduce visible leaves; mode 1 adds gray zero-normal regions. The closed doors/windows in these views do not validate traversable openings. No full-resolution visible-surface ground truth is available.',
            'time': '16-25ms per CPU grid already consumes a large fraction of the whole-frame budget. This rejects this implementation as a per-frame input; it does not prove every sparse or offline use infeasible.',
            'projection': 'First float-center view fails the original 0.5px limit. The predeclared amendment uses integer coordinates in the second view, which passes at max 0.142px. These results suggest integer unprojection; no same-view repeat or engine implementation claim.',
            'trace_dist': 'Raw TraceDist includes large signed values; ray distance here is 250 times the returned path fraction. TraceDist semantics are not assumed to be Euclidean hit distance.',
            'decision': 'Close live collision-grid integration. Preserve this offline diagnostic; no bridge, model training, material change or runnable-package change.'},
        'source_hashes': {p.relative_to(ROOT).as_posix(): digest(p) for p in sources},
        'published_media': [{'file': name, 'sha256': digest(path), 'transformation': transform} for path, name, transform in files],
        'working_package_changed': False, 'render_buffers_available': False, 'photorealistic_gain_demonstrated': False}
    write_json(target, report)
    manifest_path = ROOT / 'docs/media/manifest.json'; manifest = read(manifest_path)
    for path, name, transform in files:
        destination = ROOT / 'docs/media' / name
        if destination.exists(): raise FileExistsError(name)
        shutil.copyfile(path, destination)
        manifest['images'].append({'file': name, 'sha256': digest(destination), 'bytes': destination.stat().st_size,
            'dimensions': list(Image.open(destination).size), 'source_record': target.relative_to(ROOT).as_posix(),
            'source_artifact': path.relative_to(ROOT).as_posix(), 'source_sha256': digest(path),
            'transformation': transform, 'rights': 'Arma Reforger imagery and geometry © Bohemia Interactive, outside MIT license; original diagnostic code MIT'})
    write_json(manifest_path, manifest)
    print('Published two geometry views, all attempts and the closed live-input decision.')


if __name__ == '__main__': main()
