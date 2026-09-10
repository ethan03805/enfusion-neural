"""Publish the reviewed native roughness response and its restoration control."""
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
    target = ROOT / 'evidence/playable-material-control-v1.json'
    if target.exists(): raise FileExistsError(target)
    project = ROOT / 'runs/playable-material-control-v1'
    analysis = ROOT / 'runs/material-control-analysis-v1/report.json'
    result = read(analysis)
    if not result['passed']: raise ValueError('Declared appearance control failed')
    for path, sha in result['source_hashes'].items():
        if digest(ROOT / path) != sha: raise ValueError('Control source changed')
    plan_path = ROOT / 'scenes/playable-material-control-v1.json'
    if digest(plan_path) != read(project / 'setup.json')['plan_sha256']: raise ValueError('Pre-capture plan changed')
    validation = project / 'runs/20260910T085208-4d4509da72'
    capture = project / 'runs' / result['run']
    valid = read(validation / 'run.json'); captured = read(capture / 'run.json')
    if valid['status'] != 'succeeded' or valid['process_exit_code'] != 0 or valid['addon_sha256'] != captured['addon_sha256']:
        raise ValueError('Validation and capture differ')
    files = [(ROOT / row['path'], f'material-control-{name}.png') for name, row in result['images'].items()]
    records = [analysis, project / 'setup.json', validation / 'run.json', validation / 'console.log', capture / 'run.json']
    report = {'schema_version': 1, 'date': '2026-09-10', 'outcome': 'native_roughness_response_and_reset_verified',
        'plan': read(plan_path), 'analysis': result,
        'validation': {k: valid.get(k) for k in ['run_id', 'status', 'wall_seconds', 'process_exit_code', 'addon_sha256']},
        'capture': {k: captured.get(k) for k in ['run_id', 'status', 'wall_seconds', 'process_exit_code', 'terminated_owned_process', 'finished_at', 'image'] if k != 'image'},
        'investigation': {'started_at': '2026-09-10T08:52:07Z', 'validations': 1, 'sequences': 1, 'unused_attempts_not_run': True},
        'review': {'scope': 'All three native 1199x658 source/change/reset images inspected in full.',
            'response': 'The roof becomes strongly reflective while retaining slate layout, roof attachments and boundary. The foreground pole/barrier, facade openings and sky retain their broad appearance. Other instances of this material can also change; this is not a per-instance override.',
            'restoration': 'The roof returns visually to its original matte response and passes the declared ROI error limit. Full-frame restoration is not exact: maximum error 178 codes remains, including time-varying scene detail; no cause isolation or exact-return claim.',
            'limit': 'RoughnessScale 0.05 is an intentionally exaggerated diagnostic, not accepted dry-slate appearance, photographic ground truth or neural output. Only one static view and one material scalar are tested.',
            'decision': 'Supported in-memory material editing provides a usable reference-authoring control without decoding native textures. Next compare moderate values with documented photographic references and held-out views before accepting a material preset or training pair.'},
        'source_hashes': {p.relative_to(ROOT).as_posix(): digest(p) for p in records},
        'published_media': [{'file': name, 'sha256': digest(path), 'transformation': 'Unchanged native Workbench PNG; no alignment, rescaling, grading or neural processing'} for path, name in files],
        'native_files_modified': False, 'working_package_changed': False, 'new_neural_training': False,
        'substantial_photorealistic_gain_accepted': False}
    write_json(target, report)
    manifest_path = ROOT / 'docs/media/manifest.json'; manifest = read(manifest_path)
    for path, name in files:
        destination = ROOT / 'docs/media' / name
        if destination.exists(): raise FileExistsError(name)
        shutil.copyfile(path, destination)
        manifest['images'].append({'file': name, 'sha256': digest(destination), 'bytes': destination.stat().st_size,
            'dimensions': list(Image.open(destination).size), 'source_record': target.relative_to(ROOT).as_posix(),
            'source_artifact': path.relative_to(ROOT).as_posix(), 'source_sha256': digest(path),
            'transformation': 'Unchanged native Workbench screenshot; no resizing or neural processing',
            'rights': 'Arma Reforger imagery © Bohemia Interactive, outside MIT license'})
    write_json(manifest_path, manifest)
    print('Published the native material response, all declared controls and three unchanged images.')


if __name__ == '__main__': main()
