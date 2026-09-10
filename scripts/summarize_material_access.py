"""Retain the bounded file-access failure and successful prefab-default read."""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    destination = ROOT / 'evidence/playable-material-access-v1.json'
    if destination.exists(): raise FileExistsError('Evidence already exists')
    access_root = ROOT / 'runs/playable-material-access-v1'
    access = read(access_root / 'access.json')
    failed = access_root / 'runs' / access['run_id']
    r = read(failed / 'run.json')
    if access['status'] != 'failed' or r['status'] != 'failed' or not r['terminated_owned_process']:
        raise ValueError('Expected retained timed-out access probe')
    if any(f['output_present'] for f in access['files']) or access['records'] != [' started']:
        raise ValueError('Observed access result changed')
    for file, key in [('run.json', 'manifest_sha256'), ('console.log', 'console_sha256'), ('driver.py', 'driver_sha256')]:
        if digest(failed / file) != access[key]: raise ValueError('Access snapshot changed')
    project = ROOT / 'runs/playable-material-binding-v1'
    capture = project / 'runs/20260910T080024-5ede4d71bd'
    validation = project / 'runs/20260910T080005-432fe23335'
    result = read(capture / 'run.json'); valid = read(validation / 'run.json')
    if result['status'] != 'succeeded' or valid['status'] != 'succeeded' or valid['process_exit_code'] != 0:
        raise ValueError('Binding validation or capture incomplete')
    if digest(capture / 'frame.png') != result['image']['sha256']: raise ValueError('Capture changed')
    text = (capture / 'console.log').read_text()
    for token in ['ENR_BIND started', 'ENR_BIND completed matches=1 nodes=41', 'ENR_BIND_SOURCE available=0']:
        if text.count(token) != 1: raise ValueError('Binding observation differs')
    fields = re.findall(r'ENR_BIND_FIELD path=prefab.components\[1\] name=Materials type=141 has_default=1 default=([^\r\n]+)', text)
    if len(fields) != 1: raise ValueError('Missing unique mesh defaults')
    mapping = dict(pair.split(',', 1) for pair in fields[0].split(';'))
    identity = read(ROOT / 'evidence/playable-material-identity-v1.json')
    if set(mapping) != {s['name'] for s in identity['asset']['material_slots']}:
        raise ValueError('Default material set differs from observed slots')
    for m in identity['materials']:
        if mapping[m['slot_basename']] != m['resource']: raise ValueError('Material resource differs')
    checks = [access_root / 'access.json', failed / 'run.json', failed / 'console.log', failed / 'driver.py',
        access_root / 'runs' / access['validation_run'] / 'run.json',
        capture / 'run.json', capture / 'console.log', capture / 'addon/Scripts/Game/ENR_MaterialBinding.c',
        capture / 'addon/Scripts/Game/ELab_GameCapture.c', validation / 'run.json', validation / 'console.log',
        ROOT / 'scenes/playable-material-access-v1.json', ROOT / 'evidence/playable-material-identity-v1.json']
    report = {'schema_version': 1, 'date': '2026-09-10',
        'outcome': 'prefab_defaults_verified_texture_access_closed',
        'plan': read(ROOT / 'scenes/playable-material-access-v1.json'),
        'access': {'run': access['run_id'], 'status': r['status'], 'timeout_seconds': r['timeout_seconds'],
            'wall_seconds': r['wall_seconds'], 'terminated_owned_process': r['terminated_owned_process'],
            'process_exit_code': r['process_exit_code'], 'records': access['records'], 'files': access['files'],
            'interpretation': 'Callback started, then timed out before the first file result. No outputs. The log does not isolate whether FileExists or CopyFile stalled. Later listed files were not reached; they are not proven absent.'},
        'binding': {'run': capture.name, 'matches': 1, 'inspected_containers': 41,
            'mesh': identity['asset']['mesh'], 'origin': identity['asset']['origin'],
            'prefab_default_materials': mapping, 'override_array_count': 0, 'editor_instance_source_available': False,
            'interpretation': 'GetDefaultAsString exposes 13 native MeshObject defaults matching the observed slots. Materials GetObjectArray returns zero entries. This does not establish the absence of runtime overrides; EntityToSource returned null during simulation.'},
        'capture': {'dimensions': [1199, 658], 'sha256': digest(capture / 'frame.png'),
            'position': result['position'], 'direction': result['direction'],
            'review': 'Full native image inspected: same slate roof, facade openings, gutter, foreground pole and metal barrier. No neural processing or asset edits. Retained privately; existing equivalent published survey remains sufficient.'},
        'documented_channel_contract': {'source': 'https://community.bistudio.com/wiki/Arma_Reforger:Textures',
            'BCR': 'RGB base color in sRGB; alpha roughness',
            'NMO': 'Linear RGBA: normal +X, normal -Y, metalness, ambient occlusion',
            'MCR': 'Macro color RGB, roughness alpha; color space depends on import settings',
            'actual_texture_dimensions': None, 'actual_texture_pixels_validated': False},
        'source_hashes': {p.relative_to(ROOT).as_posix(): digest(p) for p in checks},
        'live_companion_changed': False, 'aligned_photorealistic_target_available': False,
        'next': 'Close this bounded native-file route. Evaluate a small RGB restoration model against an explicitly declared source-preservation control before live integration. Restoration alone does not meet the separate material/lighting goal.'}
    write_json(destination, report)
    print('Retained timed-out access probe and 13 verified prefab defaults; no texture pixels or per-instance binding claimed.')


if __name__ == '__main__': main()
