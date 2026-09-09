"""Original texture-build provenance and bounded material control recipes."""
import json
from pathlib import Path
import re
import struct

from .references import digest


def load_build(root, repository):
    root = Path(root).resolve()
    report_path = root / 'build.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    run = (root / 'runs' / report['run_id']).resolve()
    if root not in run.parents or digest(run / 'run.json') != report['run_manifest_sha256']:
        raise ValueError('Texture build manifest path/hash differs')
    native = json.loads((run / 'run.json').read_text(encoding='utf-8'))
    validation_path = (root / 'runs' / report['validation_run'] / 'run.json').resolve()
    if root not in validation_path.parents or digest(validation_path) != report['validation_manifest_sha256']:
        raise ValueError('Texture compile validation differs')
    validation = json.loads(validation_path.read_text(encoding='utf-8'))
    if (report['status'] != 'succeeded' or report['operation'] != 'original-texture-build'
            or native['status'] != 'succeeded' or not native['alive_after_build_observation']
            or native['stable_output_observation_seconds'] < 10
            or validation['status'] != 'succeeded' or validation['process_exit_code'] != 0
            or digest(run / 'driver.py') != report['driver_sha256']
            or digest(run / 'addon/Scripts/WorkbenchGame/ENR_TextureBuildPlugin.c') != report['plugin_sha256']
            or digest(run / 'console.log') != report['console_sha256']):
        raise ValueError('Texture build is incomplete or changed')
    log = (run / 'console.log').read_text(encoding='utf-8')
    if 'ENR_TEXTURE queued=18' not in log or log.count('Build successful') < 18:
        raise ValueError('Texture build completion records missing')
    plan_path = Path(repository) / 'scenes/material-room-texture-control-v1.json'
    if report['source']['plan_sha256'] != digest(plan_path) or report['source']['plan'] != json.loads(plan_path.read_text(encoding='utf-8')):
        raise ValueError('Texture plan changed')
    if report['source']['source_scene_sha256'] != digest(Path(repository) / report['source']['plan']['source_scene']):
        raise ValueError('Original material constants changed')
    assets = run / 'addon/Assets/ENR_OriginalTextures'
    copies = []
    seen = set()
    for asset in report['retained_assets']:
        path = (assets / asset['file']).resolve()
        if assets not in path.parents or path in seen or digest(path) != asset['sha256']:
            raise ValueError('Texture asset path/hash differs')
        seen.add(path)
        copies.append((path, asset['file']))
    if len(copies) != 54:
        raise ValueError('Expected sources, metadata and compiled outputs for eighteen textures')
    headers = []
    names = set()
    for item in report['identities']:
        name = item['name']
        if name in names or not re.fullmatch(r'[a-z_]+_(BCR|NMO)', name):
            raise ValueError('Duplicate or unexpected texture identity')
        names.add(name)
        expected = r'\{[0-9A-F]{16}\}Assets/ENR_OriginalTextures/' + re.escape(name) + r'\.edds'
        if not re.fullmatch(expected, item['resource']):
            raise ValueError('Unexpected texture resource GUID/path')
        source = assets / item['source']
        if digest(source) != item['source_sha256']:
            raise ValueError('Texture source changed during native import')
        metadata = (assets / (name + '.edds.meta')).read_text(encoding='utf-8')
        if 'Name "' + item['resource'] + '"' not in metadata:
            raise ValueError('Compiled texture metadata identity differs')
        compiled = (assets / (name + '.edds')).read_bytes()
        if len(compiled) < 148 or compiled[:4] != b'DDS ' or compiled[84:88] != b'DX10':
            raise ValueError('Expected DDS/DX10 header')
        height, width = struct.unpack_from('<II', compiled, 12)
        mips = struct.unpack_from('<I', compiled, 28)[0]
        dxgi = struct.unpack_from('<I', compiled, 128)[0]
        expected_format = 99 if item['color_space'] == 'ToSRGB' else 98
        if (width, height, mips, dxgi) != (512, 512, 10, expected_format):
            raise ValueError('Unexpected compiled dimensions/mips/color format')
        headers.append({'name': name, 'width': width, 'height': height, 'mips': mips, 'dxgi_format': dxgi,
                        'container_tag_hex': compiled[36:40].hex(), 'pixel_decode_verified': False})
    if len(names) != 18:
        raise ValueError('Expected eighteen resource identities')
    return report, copies, {'build_report_sha256': digest(report_path), 'run_id': report['run_id'],
                           'run_manifest_sha256': report['run_manifest_sha256'], 'compiled_headers': headers}


def material_recipe(case, materials, identities):
    if case not in ('orientation', 'packed', 'metal-matte', 'metal-dielectric'):
        raise ValueError('Unknown original texture control')
    resources = {item['name']: item['resource'] for item in identities}
    recipes = []
    for name, values in sorted(materials.items()):
        bcr = nmo = None
        rgba = [1, 1, 1, 1]
        if case == 'orientation' and name != 'neutral':
            rgba = values['base_color_linear'] + [1]
        else:
            prefix = 'orientation' if case == 'orientation' else name
            bcr_name, nmo_name = prefix + '_BCR', prefix + '_NMO'
            if case == 'metal-matte' and name == 'metal':
                bcr_name = 'metal_matte_BCR'
            if case == 'metal-dielectric' and name == 'metal':
                nmo_name = 'metal_dielectric_NMO'
            bcr, nmo = resources[bcr_name], resources[nmo_name]
        text = 'MatPBRBasic {\n Color ' + ' '.join(format(v, '.9g') for v in rgba) + '\n'
        if bcr:
            text += ' BCRMap "' + bcr + '"\n NMOMap "' + nmo + '"\n'
        text += '}\n'
        recipes.append({'name': name, 'rgba': rgba, 'bcr': bcr, 'nmo': nmo, 'material_text': text})
    return recipes


def verify_map_records(records, materials):
    """Require every declared map and retain the native resource suffix explicitly."""
    expected = {m['name']: m for m in materials}
    observed = {}
    for line in records:
        match = re.fullmatch(r'slot=([\w-]+) bcr_read=1 bcr=(.*?) nmo_read=1 nmo=(.*)', line)
        if not match or match[1] not in expected or match[1] in observed:
            raise ValueError('Missing, duplicate or failed native map readback')
        item = expected[match[1]]
        maps = {}
        for field, raw in [('bcr', match[2]), ('nmo', match[3])]:
            resource = item[field]
            required = resource + ' 0' if resource else ''
            if raw != required:
                raise ValueError('Native map differs from declared material: ' + match[1] + '/' + field)
            maps[field] = {'resource': resource, 'native_raw': raw, 'native_suffix': ' 0' if resource else None}
        observed[match[1]] = maps
    if set(observed) != set(expected):
        raise ValueError('Native map readback omits a material')
    return observed
