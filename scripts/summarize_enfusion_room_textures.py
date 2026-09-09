"""Verify four original packed-texture controls and retain their measured scope."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr import room_textures
from enr.references import digest
from summarize_enfusion_room_geometry import capture_trial, import_trial


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def changed_channels(before, after):
    if before.shape != after.shape or before.ndim != 3 or before.shape[-1] != 4:
        raise ValueError('Texture controls require matching RGBA images')
    return np.flatnonzero(np.any(before != after, axis=(0, 1))).tolist()


def trial(root, load, built, provenance):
    root = Path(root).resolve()
    report = read(root / 'room.json')
    result = capture_trial(root)
    run = root / 'runs' / report['run_id']
    native = read(run / 'run.json')
    control = read(root / 'texture-control.json')
    if (control != report['texture_control'] or digest(root / 'texture-control.json') != report['texture_control_sha256']
            or control['build'] != provenance or control['plan'] != built['source']['plan']
            or control['plan_sha256'] != built['source']['plan_sha256']
            or control['texture_assets'] != built['retained_assets']
            or report['driver_sha256'] != digest(root / 'capture_driver.py')
            or report['source_import_report_sha256'] != load['report_sha256']):
        raise ValueError('Texture capture provenance differs')
    scene = read(ROOT / control['plan']['source_scene'])
    recipes = room_textures.material_recipe(control['case'], scene['materials'], built['identities'])
    if len(control['materials']) != len(recipes):
        raise ValueError('Missing original material recipe')
    changes = {}
    for expected, actual in zip(recipes, control['materials']):
        if any(actual[key] != value for key, value in expected.items()):
            raise ValueError('Unexpected material recipe')
        changes['Data/' + actual['name'] + '.emat'] = actual
    for original in load['retained_assets']:
        name = original['file']
        path = run / 'addon/Assets/ENR_ReferenceRoom' / name
        expected_hash = changes[name]['after_sha256'] if name in changes else original['sha256']
        if digest(path) != expected_hash or native['addon_sha256']['Assets/ENR_ReferenceRoom/' + name] != expected_hash:
            raise ValueError('Captured room asset differs')
        if name in changes and (changes[name]['before_sha256'] != original['sha256']
                                or path.read_bytes() != changes[name]['material_text'].encode('utf-8')):
            raise ValueError('Material changed beyond declared recipe')
    for asset in built['retained_assets']:
        name = 'Assets/ENR_OriginalTextures/' + asset['file']
        if digest(run / 'addon' / name) != asset['sha256'] or native['addon_sha256'][name] != asset['sha256']:
            raise ValueError('Texture changed between build and capture')
    log = (run / 'console.log').read_text(encoding='utf-8')
    maps = [s.split('ENR_ROOM_MAP ', 1)[1] for s in log.splitlines() if 'ENR_ROOM_MAP ' in s]
    colors = [s.split('ENR_ROOM_COLOR ', 1)[1] for s in log.splitlines() if 'ENR_ROOM_COLOR ' in s]
    if maps != report['texture_records'] or colors != report['color_records']:
        raise ValueError('Material readback differs from native log')
    observed = room_textures.verify_map_records(maps, recipes)
    color_values = {}
    for line in colors:
        match = re.fullmatch(r'resource=([\w-]+) read=1 rgba=([0-9.eE+\- ]+)', line)
        if not match or match[1] in color_values:
            raise ValueError('Failed or duplicate Color readback')
        color_values[match[1]] = [float(v) for v in match[2].split()]
    if color_values != {r['name']: r['rgba'] for r in recipes}:
        raise ValueError('Native material Color differs')
    frame = report['frames'][0]
    path = run / frame['file']
    if digest(path) != frame['sha256']:
        raise ValueError('Captured image changed')
    image = np.asarray(Image.open(path).convert('RGB'), dtype=np.float64)
    result.pop('visual_review')
    result.update(case=control['case'], control=control, driver_sha256=report['driver_sha256'],
                  native_maps=observed, native_colors=color_values,
                  image={'file': frame['file'].replace('\\', '/'), 'sha256': digest(path),
                         'bytes': path.stat().st_size, 'dimensions': report['dimensions']})
    return result, image, report['config']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures', nargs=4, required=True)
    parser.add_argument('--loaded-import', required=True)
    parser.add_argument('--texture-source', required=True)
    parser.add_argument('--texture-build', required=True)
    parser.add_argument('--orientation-check', required=True)
    parser.add_argument('--review', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists():
        raise ValueError('Choose a new evidence path')
    load = import_trial(args.loaded_import)
    built, copies, provenance = room_textures.load_build(args.texture_build, ROOT)
    source_root = Path(args.texture_source)
    source = read(source_root / 'textures.json')
    if (source != built['source'] or digest(source_root / 'textures.json') != built['source_report_sha256']
            or digest(source_root / 'generator.py') != source['generator_sha256']):
        raise ValueError('Original texture source provenance differs')
    pixels = {}
    for item in source['textures']:
        path = source_root / item['file']
        values = np.asarray(Image.open(path))
        if (digest(path) != item['sha256'] or values.shape != (512, 512, 4) or values.dtype != np.uint8
                or hashlib.sha256(values.tobytes()).hexdigest() != item['pixel_sha256']):
            raise ValueError('Original texture pixels differ')
        pixels[item['name']] = values
    roughness_channels = changed_channels(pixels['metal_BCR'], pixels['metal_matte_BCR'])
    metalness_channels = changed_channels(pixels['metal_NMO'], pixels['metal_dielectric_NMO'])
    if roughness_channels != [3] or metalness_channels != [2]:
        raise ValueError('A source control changes additional channels')
    controls, images, configs = [], {}, []
    for root in args.captures:
        result, image, config = trial(root, load, built, provenance)
        if result['case'] in images:
            raise ValueError('Duplicate control case')
        controls.append(result)
        images[result['case']] = image
        configs.append(config)
    if set(images) != set(source['plan']['cases']) or any(c != configs[0] for c in configs):
        raise ValueError('Cases missing or capture configuration differs')
    review = read(args.review)
    for result in controls:
        matches = [r for r in review['frames'] if r['case'] == result['case']]
        if (len(matches) != 1 or matches[0]['sha256'] != result['image']['sha256']
                or matches[0]['dimensions'] != result['dimensions'] or not matches[0]['full_size_inspected']):
            raise ValueError('Missing hash-bound visual inspection')
        result['visual_review'] = matches[0]['observation']
    orientation = read(args.orientation_check)
    orient_control = next(c for c in controls if c['case'] == 'orientation')
    if (orientation['capture_report_sha256'] != orient_control['report_sha256']
            or orientation['frame_sha256'] != orient_control['image']['sha256']
            or orientation['texture_build_report_sha256'] != provenance['build_report_sha256']
            or orientation['script_sha256'] != digest(Path(args.orientation_check).with_suffix('.py'))
            or orientation['plan_sha256'] != source['plan_sha256']
            or orientation['source_texture_sha256'] != digest(source_root / 'orientation_BCR.tif')):
        raise ValueError('Orientation evidence binding differs')
    x0, y0, x1, y1 = source['plan']['response_region_xyxy']
    height, width = images['packed'].shape[:2]
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise ValueError('Declared response region outside image')
    responses = []
    for case in ('metal-matte', 'metal-dielectric'):
        difference = np.abs(images[case] - images['packed'])
        responses.append({'before': 'packed', 'after': case, 'region_xyxy': [x0, y0, x1, y1],
                          'region_rgb8_mae': float(difference[y0:y1, x0:x1].mean()),
                          'full_rgb8_mae': float(difference.mean()),
                          'region_before_mean_rgb8': images['packed'][y0:y1, x0:x1].mean(axis=(0, 1)).tolist(),
                          'region_after_mean_rgb8': images[case][y0:y1, x0:x1].mean(axis=(0, 1)).tolist()})
    result = {'schema_version': 1, 'operation': 'original-room-packed-texture-controls',
              'evidence_verification': 'succeeded', 'summarizer_sha256': digest(__file__),
              'plan': source['plan'], 'plan_sha256': source['plan_sha256'], 'source': source,
              'build': dict(provenance, report=built), 'loaded_import': load, 'controls': controls,
              'visual_review_sha256': digest(args.review), 'orientation': orientation,
              'orientation_report_sha256': digest(args.orientation_check),
              'source_changed_channels_zero_based': {'roughness': roughness_channels, 'metalness': metalness_channels},
              'responses': responses,
              'verified': {'native_texture_build_and_load': True, 'declared_map_readback': True,
                           'single_channel_source_controls': True,
                           'back_wall_orientation_diagnostic': orientation['status'] == 'succeeded',
                           'region_response_nonzero': all(r['region_rgb8_mae'] > 0 for r in responses),
                           'physical_roughness_calibration': False, 'reference_photometry': False,
                           'aligned_appearance_pair': False, 'renderer_integration': False},
              'scope': 'Original material/texture response in one native room/camera; no model processing.',
              'limits': ['One capture per case; no estimate of repeat variation or motion stability in this batch',
                         'Header format is checked; Enfusion payload is not independently decoded',
                         'Roughness alpha is a candidate direct encoding, not a calibrated Cycles BRDF match',
                         'The shiny sphere reflects surrounding scenery; environment/reflection control remains open',
                         'Four back-wall orientation samples do not validate all surfaces, mips or tangent-space normals',
                         'Earlier strict TXO precision failures remain failed',
                         'No matched reference, live model, scene buffers or complete-frame performance proof'],
              'next': 'Control surrounding light/reflections and establish exposure/color mapping before an engine/reference lighting pair.'}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes((json.dumps(result, indent=2, allow_nan=False) + '\n').encode('utf-8'))
    print(json.dumps({'verified': result['verified'], 'responses': responses, 'images': [c['image'] for c in controls]}))


if __name__ == '__main__':
    main()
