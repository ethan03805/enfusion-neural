"""Bind the reviewed street building to observed mesh slots and material records.

Requires retained local Workbench runs. Publishes metadata and one reviewed
survey image, never source textures, meshes or a claimed training pair.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil

from probe_enfusion_material_schema import verified_inventory

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    evidence = ROOT / 'evidence/playable-material-identity-v1.json'
    destination = ROOT / 'docs/media/playable-street-material.png'
    if evidence.exists() or destination.exists():
        raise FileExistsError('The material evidence is already published')
    project = ROOT / 'runs/playable-material-identity-v1'
    first = project / 'runs/20260910T073240-d1eb69b461'
    closeup = project / 'runs/20260910T073835-de8e0accc3'
    text = (first / 'console.log').read_text()
    if text.count('ENR_IDENTITY started') != 1 or text.count('ENR_IDENTITY completed') != 1:
        raise ValueError('Incomplete asset inspection')
    objects = re.findall(r'ENR_IDENTITY_OBJECT id=(\d+) origin=<([^>]+)> mesh=(\S+) prefab=(\S*) materials=(\d+) mins=<([^>]+)> maxs=<([^>]+)>', text)
    selected = [r for r in objects if r[0] == '14']
    if len(selected) != 1 or 'House_Village_E_1L02t.xob' not in selected[0][2]:
        raise ValueError('Selected gameplay asset changed')
    row = selected[0]
    slots = re.findall(r'ENR_IDENTITY_SLOT id=14 index=(\d+) value=(\S+)', text)
    observed, inventory = verified_inventory(ROOT / 'runs/playable-material-resources-v1/resources.json')
    schema_root = ROOT / 'runs/playable-material-schema-v1'
    schema = read(schema_root / 'schema.json')
    schema_run = schema_root / 'runs' / schema['run_id']
    record = read(schema_run / 'run.json')
    if schema['status'] != 'succeeded' or record['process_exit_code'] != 0 or record['terminated_owned_process']:
        raise ValueError('Material inspection did not exit naturally')
    if sha(schema_run / 'run.json') != schema['manifest_sha256'] or sha(schema_run / 'console.log') != schema['console_sha256']:
        raise ValueError('Material inspection provenance changed')
    materials = []
    for item in schema['materials']:
        if item['resource'] not in observed:
            raise ValueError('Material not in native inventory')
        stem = item['resource'].rsplit('/', 1)[1].removesuffix('.emat')
        if stem not in dict(slots).values():
            raise ValueError('Material basename does not match observed mesh slot')
        same_name = [x for x in observed if x.endswith('/' + stem + '.emat')]
        if len(same_name) != 1:
            raise ValueError('Ambiguous material name')
        maps = []
        for line in schema['records']:
            m = re.fullmatch(r'_TEXT path=' + re.escape(item['name']) + r' name=(\S+) read=1 value=(\{[A-F0-9]{16}\}\S+\.edds)(.*)', line)
            if m:
                maps.append({'field': m[1], 'resource': m[2], 'serialized_suffix': m[3].strip()})
        materials.append({**item, 'slot_basename': stem, 'class': 'MatPBRMulti', 'texture_references': maps})
    captures = []
    for folder in [first, closeup]:
        r = read(folder / 'run.json')
        if r['status'] != 'succeeded' or sha(folder / 'frame.png') != r['image']['sha256']:
            raise ValueError('Unverified survey capture')
        captures.append({'run': folder.name, 'dimensions': [r['image']['width'], r['image']['height']],
                         'position': r['position'], 'direction': r['direction'],
                         'image_sha256': sha(folder / 'frame.png'), 'manifest_sha256': sha(folder / 'run.json'),
                         'console_sha256': sha(folder / 'console.log'), 'scope': 'Native Workbench identity survey, not the fixed gameplay render/profile or a photorealistic target'})
    validation = project / 'runs/20260910T073216-dc3709b83a'
    checks = [validation / 'run.json', validation / 'console.log',
              schema_root / 'schema.json', ROOT / 'runs/playable-material-resources-v1/resources.json',
              ROOT / 'scenes/playable-material-identity-v1.json', ROOT / 'scenes/playable-material-schema-v1.json',
              ROOT / 'adapters/enfusion/probes/ENR_MaterialIdentity.c', ROOT / 'scripts/probe_enfusion_material_schema.py',
              ROOT / 'runs/foliage-walk-pilot-v3/analysis.json']
    report = {'schema_version': 1, 'date': '2026-09-10', 'outcome': 'material_resource_references_observed',
              'asset': {'mesh': row[2], 'prefab': row[3], 'origin': list(map(float, row[1].split(','))),
                        'material_slots': [{'index': int(i), 'name': name} for i, name in slots]},
              'inspection_limit': 'The 45m sphere encountered 975 objects; the predeclared first 160 were inspected, yielding 423 slots. Slots are names, not direct material handles; initial direct container count was zero. This is not an exhaustive town inventory.',
              'association': 'Three unique material basenames exactly match mesh slot names and share the mesh asset folder. Their resource containers load successfully. This establishes a strong asset-family association; it does not yet verify active per-instance overrides or every rendered pixel.',
              'materials': materials, 'native_inventory': inventory, 'captures': captures,
              'review': 'Both full 1199x658 surveys inspected. The second shows the existing long slate-roof house, facade openings, gutter, foreground pole and metal barrier. No neural processing, cropping, paint-over or asset replacement.',
              'reference_limit': 'The slate/plaster/brick resource references are actual native material inputs, not decoded images or higher-fidelity paired ground truth. No texture bytes are extracted or published and no model is trained.',
              'next': 'Verify the mesh default/per-instance binding, then test supported read-only access to its existing slate BCR/NMO and mask data. Validate dimensions/channel meaning before defining any learned correction. Keep doors, windows, roof pattern and cover as constraints.',
              'source_hashes': {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in checks}}
    evidence.write_text(json.dumps(report, indent=2), encoding='utf-8')
    shutil.copyfile(closeup / 'frame.png', destination)
    manifest_path = ROOT / 'docs/media/manifest.json'
    manifest = read(manifest_path)
    manifest['images'].append({'file': destination.name, 'sha256': sha(destination), 'bytes': destination.stat().st_size,
                               'dimensions': [1199, 658], 'source_record': str(evidence.relative_to(ROOT)).replace('\\', '/'),
                               'source_artifact': str((closeup / 'frame.png').relative_to(ROOT)).replace('\\', '/'),
                               'source_sha256': sha(closeup / 'frame.png'), 'transformation': 'None; complete native Workbench survey PNG',
                               'rights': 'Arma Reforger imagery © Bohemia Interactive; outside MIT code license'})
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Published three observed material-reference records and one reviewed identity survey; no training target claimed.')


if __name__ == '__main__':
    main()
