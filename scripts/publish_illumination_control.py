"""Publish the bounded native illumination failure and unchanged reviewed frames."""
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
    target = ROOT / 'evidence/playable-illumination-v1.json'
    if target.exists():
        raise FileExistsError(target)
    plan_path = ROOT / 'scenes/playable-illumination-v1.json'
    selection_path = ROOT / 'scenes/playable-illumination-control-v1.json'
    plan, selection = read(plan_path), read(selection_path)
    inventory = ROOT / selection['inventory_run']
    analysis_path = ROOT / 'runs/illumination-control-analysis-v1/report.json'
    result = read(analysis_path); control = ROOT / result['run']
    if digest(plan_path) != selection['parent_plan_sha256'] or digest(inventory / 'console.log') != selection['inventory_console_sha256']:
        raise ValueError('Changed plan/inventory')
    for path, sha in result['source_hashes'].items():
        if digest(ROOT / path) != sha:
            raise ValueError('Changed analyzed artifact: ' + path)
    pairs = [
        (inventory.parent / '20260910T101416-cd29daeb39', inventory),
        (control.parent / '20260910T101804-534395cd34', control),
    ]
    runs = []; records = [plan_path, selection_path, analysis_path, Path(__file__)]
    for validation, capture in pairs:
        valid, captured = read(validation / 'run.json'), read(capture / 'run.json')
        if valid['status'] != 'succeeded' or valid['process_exit_code'] != 0 or valid['terminated_owned_process']:
            raise ValueError('Unverified compilation')
        if captured['status'] != 'succeeded' or valid['addon_sha256'] != captured['addon_sha256']:
            raise ValueError('Validation and capture differ')
        if digest(capture / 'frame.png') != captured['image']['sha256']:
            raise ValueError('Changed capture')
        for folder, manifest in ((validation, valid), (capture, captured)):
            for path, sha in manifest['addon_sha256'].items():
                if digest(folder / 'addon' / path) != sha:
                    raise ValueError('Changed retained addon')
            records.extend([folder / 'run.json', folder / 'console.log'])
        project = capture.parent.parent
        setup = read(project / 'setup.json')
        for path, sha in setup['source_hashes'].items():
            if digest(ROOT / path) != sha:
                raise ValueError('Changed setup source')
        records.extend([project / 'setup.json', project / 'setup-driver.py'])
        runs.append({'validation': {k: valid[k] for k in ('run_id', 'status', 'process_exit_code', 'wall_seconds', 'addon_sha256')},
                     'capture': {k: captured[k] for k in ('run_id', 'status', 'process_exit_code', 'terminated_owned_process', 'wall_seconds', 'finished_at', 'events')},
                     'image_sha256': captured['image']['sha256']})
    log = (inventory / 'console.log').read_text()
    if log.count('ENR_ILLUM completed scanned=5000 found=2 limit=1') != 1:
        raise ValueError('Changed bounded inventory result')
    selected_names = ('SkyIntensityLV', 'GroundIntensityLV', 'DiffuseIBL', 'AerialPerspectiveStrength',
                      'DirectLightLV', 'IndirectLightLV', 'ProbeReflectionEV', 'ProbeDiffuseEV')
    selected_records = [line.split('ENR_ILLUM_', 1)[1] for line in log.splitlines()
                        if 'ENR_ILLUM_' in line and (any(' name=' + n + ' ' in line for n in selected_names)
                        or 'ENR_ILLUM_SKY' in line or 'ENR_ILLUM_PREFAB' in line)]
    files = [(ROOT / row['path'], f'illumination-{name}.png') for name, row in result['images'].items()]
    for path, name in files:
        if (ROOT / 'docs/media' / name).exists() or Image.open(path).size != (1199,658):
            raise ValueError('Unexpected media destination/dimensions')
    closed = datetime.now(timezone.utc)
    elapsed = (closed-datetime.fromisoformat(plan['started_at'].replace('Z', '+00:00'))).total_seconds()/60
    report = {'schema_version': 1, 'date': '2026-09-10', 'outcome': 'sky_scalar_assignment_without_useful_visible_response',
        'evaluation_closed_at': closed.isoformat(), 'minutes_since_plan_start': elapsed,
        'within_declared_time_bound': elapsed <= plan['maximum_minutes'],
        'plan': plan, 'selected_control': selection, 'analysis': result, 'runs': runs,
        'inventory': {'scanned_entity_ids': 5000, 'first_subscene_entity_count': 1404627,
            'matched_world_or_light_entities': 2, 'scan_limit_reached': True,
            'scope': 'Bounded prefix of the first subscene, not an exhaustive world inventory. Resource/prefab values are not active scalar readback; EntityToSource produced no instance container.',
            'selected_records': selected_records, 'reviewed_source_image_sha256': digest(inventory / 'frame.png')},
        'review': {'scope': 'Inventory capture and all three complete control PNGs inspected at native 1199x658.',
            'appearance': 'No useful sky or surface-lighting change is visible. Roof tone, slate detail, facade shading, openings, pole and foreground barrier retain the same broad appearance.',
            'decision': 'Reject the candidate in the selection view. Do not run the unused reserved view, train against the image pair, retry the same scalar or change the playable package.',
            'evidence_limit': 'Index 83 and SetParam success establish assignment acceptance only. Roof change 0.0424 codes is comparable to reset difference 0.0353; sky change is 0.000144 codes. The run does not isolate an ignored parameter, weather overwrite or cached-atmosphere update behavior. It also does not prove all native illumination controls ineffective.',
            'restoration': 'Roof restoration and clipping controls pass, but full-frame reset is not exact: maximum 206 codes. With no useful changed response, this cannot validate restoration of a substantial lighting edit.'},
        'reserved_view_run': False, 'native_files_modified': False, 'working_package_changed': False,
        'training_performed': False, 'photorealistic_gain_accepted': False,
        'source_hashes': {path.relative_to(ROOT).as_posix(): digest(path) for path in records},
        'published_media': [{'file': name, 'sha256': digest(path), 'transformation': 'Unchanged native Workbench PNG; no alignment, grading, rescaling or neural processing.'} for path, name in files]}
    write_json(target, report)
    manifest_path = ROOT / 'docs/media/manifest.json'; manifest = read(manifest_path)
    for path, name in files:
        destination = ROOT / 'docs/media' / name; shutil.copyfile(path, destination)
        manifest['images'].append({'file': name, 'sha256': digest(destination), 'bytes': destination.stat().st_size,
            'dimensions': [1199,658], 'source_record': target.relative_to(ROOT).as_posix(),
            'source_artifact': path.relative_to(ROOT).as_posix(), 'source_sha256': digest(path),
            'transformation': 'Unchanged native Workbench screenshot; no resizing or neural processing.',
            'rights': 'Arma Reforger imagery © Bohemia Interactive, outside MIT license'})
    write_json(manifest_path, manifest)
    print(json.dumps({'elapsed_minutes': elapsed, 'within_bound': report['within_declared_time_bound'], 'published_images': 3}))


if __name__ == '__main__':
    main()
