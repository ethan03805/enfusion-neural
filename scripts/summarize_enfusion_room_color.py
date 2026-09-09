"""Verify original-room Color-only controls, image response and retained failure."""
import argparse
import json
from pathlib import Path
import re
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest
from summarize_enfusion_room_geometry import capture_trial, import_trial


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def trial(root, load, plan_path):
    root = Path(root).resolve()
    report = read(root / 'room.json')
    result = capture_trial(root)
    run = root / 'runs' / report['run_id']
    native = read(run / 'run.json')
    control = read(root / 'color-control.json')
    if (control != report['color_control'] or digest(root / 'color-control.json') != report['color_control_sha256']
            or control['plan_sha256'] != digest(plan_path) or control['plan'] != read(plan_path)
            or control['source_scene_sha256'] != digest(ROOT / control['plan']['source_scene'])
            or report['driver_sha256'] != digest(root / 'capture_driver.py')
            or report['source_import_report_sha256'] != load['report_sha256']):
        raise ValueError('Color control provenance differs')
    scene = read(ROOT / control['plan']['source_scene'])
    expected = {}
    for item in control['materials']:
        name = item['name']
        rgba = scene['materials'][name]['base_color_linear'] + [1] if control['case'] == 'reference-colors' else [1, 1, 1, 1]
        if rgba != item['rgba'] or name in expected:
            raise ValueError('Unexpected material constants')
        expected[name] = rgba
    if set(expected) != set(scene['materials']):
        raise ValueError('Missing original materials')
    original_assets = {a['file']: a['sha256'] for a in load['retained_assets']}
    changes = {'Data/' + a['name'] + '.emat': a for a in control['materials']}
    for name, original_hash in original_assets.items():
        path = run / 'addon/Assets/ENR_ReferenceRoom' / name
        required_hash = changes[name]['after_sha256'] if name in changes else original_hash
        if digest(path) != required_hash or native['addon_sha256']['Assets/ENR_ReferenceRoom/' + name] != required_hash:
            raise ValueError('Native snapshot asset changed')
        if name in changes:
            item = changes[name]
            text = 'MatPBRBasic {\n Color ' + ' '.join(format(v, '.9g') for v in item['rgba']) + '\n}\n'
            if item['before_sha256'] != original_hash or path.read_bytes() != text.encode('utf-8'):
                raise ValueError('Control changes more than the declared Color field')
    log = (run / 'console.log').read_text(encoding='utf-8')
    lines = [line.split('ENR_ROOM_COLOR ', 1)[1] for line in log.splitlines() if 'ENR_ROOM_COLOR ' in line]
    if lines != report['color_records'] or len(lines) != 7:
        raise ValueError('Material readback differs from native log')
    actual = {}
    for line in lines:
        match = re.fullmatch(r'resource=([\w-]+) read=1 rgba=([0-9.eE+\- ]+)', line)
        if not match or match[1] in actual:
            raise ValueError('Failed or duplicate native material readback')
        values = np.asarray([float(v) for v in match[2].split()])
        if values.shape != (4,) or not np.isfinite(values).all() or match[1] not in expected:
            raise ValueError('Invalid native color values')
        actual[match[1]] = values.tolist()
    error = max(float(np.abs(np.asarray(actual[k])-expected[k]).max()) for k in expected)
    frame = report['frames'][0]
    image_path = run / frame['file']
    if digest(image_path) != frame['sha256']:
        raise ValueError('Color control image changed')
    image = np.asarray(Image.open(image_path).convert('RGB'), dtype=np.float64)
    region_means = {}
    for name, (x0, y0, x1, y1) in control['plan']['regions_xyxy'].items():
        if not (0 <= x0 < x1 <= image.shape[1] and 0 <= y0 < y1 <= image.shape[0]):
            raise ValueError('Declared region outside image')
        region_means[name] = image[y0:y1, x0:x1].mean(axis=(0, 1)).tolist()
    result.update(case=control['case'], control=control, driver_sha256=report['driver_sha256'],
                  native_readback_rgba=actual, native_readback_max_error=error,
                  native_readback_passed=error <= control['plan']['positive_control']['native_color_readback_tolerance'],
                  region_mean_rgb8=region_means,
                  image={'file': frame['file'].replace('\\', '/'), 'sha256': digest(image_path), 'bytes': image_path.stat().st_size, 'dimensions': report['dimensions']},
                  visual_review=('All room objects remain visible with white constants.' if control['case'] == 'white' else
                                 'Red left wall, blue right wall, neutral back/floor/plinth, brown box/right sphere and dark posts are visible. White and intended-metal spheres remain visually nonmetallic under default packed-map parameters.'),
                  appearance_pair_verified=False)
    return result, image, report['config']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--white', required=True)
    parser.add_argument('--colors', required=True)
    parser.add_argument('--loaded-import', required=True)
    parser.add_argument('--failed-root', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists():
        raise ValueError('Choose a new evidence path')
    plan_path = ROOT / 'scenes/material-room-color-control-v1.json'
    load = import_trial(args.loaded_import)
    white, white_image, white_config = trial(args.white, load, plan_path)
    colors, color_image, color_config = trial(args.colors, load, plan_path)
    if white['case'] != 'white' or colors['case'] != 'reference-colors' or white_config != color_config:
        raise ValueError('Expected two cases with identical capture configurations')
    left = colors['region_mean_rgb8']['left_wall']
    right = colors['region_mean_rgb8']['right_wall']
    response = {'left_red_margin_rgb8': left[0] - max(left[1:]),
                'right_blue_margin_rgb8': right[2] - max(right[:2]), 'required_margin_rgb8': 20}
    response['passed'] = response['left_red_margin_rgb8'] > 20 and response['right_blue_margin_rgb8'] > 20
    failed_root = Path(args.failed_root).resolve()
    runs = [(p, read(p)) for p in (failed_root / 'runs').glob('*/run.json')]
    failed = [(p, r) for p, r in runs if r['command'] == 'capture']
    validations = [(p, r) for p, r in runs if r['command'] == 'validate']
    if len(failed) != 1 or len(validations) != 1:
        raise ValueError('Expected one failed control and its compile validation')
    failed_path, failure = failed[0]
    validate_path, validation = validations[0]
    failed_log = failed_path.parent / 'console.log'
    text = failed_log.read_text(encoding='utf-8')
    if failure['status'] != 'failed' or failure['exit_code'] != 3 or validation['status'] != 'succeeded' or validation['process_exit_code'] != 0:
        raise ValueError('Unexpected initial-control outcome')
    if 'Wrong GUID/name for resource @"{0000000000000000}neutral"' not in text:
        raise ValueError('Expected material-slot/resource-path diagnostic missing')
    result = {'schema_version': 1, 'operation': 'original-room-color-constant-control', 'summarizer_sha256': digest(__file__),
              'evidence_verification': 'succeeded', 'plan_sha256': digest(plan_path), 'plan': read(plan_path),
              'loaded_import': load, 'controls': [white, colors],
              'positive_control': response,
              'full_image_difference_rgb8_mae': float(np.abs(white_image-color_image).mean()),
              'failed_initial_control': {'run_id': failure['run_id'], 'run_manifest_sha256': digest(failed_path),
                  'validation_run': validation['run_id'], 'validation_manifest_sha256': digest(validate_path),
                  'console_sha256': digest(failed_log), 'native_script_sha256': digest(failed_path.parent / 'addon/Scripts/Game/ENR_MaterialRoom.c'),
                  'status': failure['status'], 'exit_code': failure['exit_code'], 'native_exit_code': failure['process_exit_code'],
                  'terminated_owned_process': failure['terminated_owned_process'], 'error': failure['error'],
                  'cause': 'Probe treated GetMaterials slot names as resource paths. Fixed by binding each original slot to its verified .emat.meta GUID before LoadContainer.'},
              'verified': {'native_color_readback': white['native_readback_passed'] and colors['native_readback_passed'],
                  'wall_color_response': response['passed'], 'only_color_constants_changed': True,
                  'reference_photometry': False, 'roughness_and_metalness': False,
                  'aligned_appearance_pair': False, 'renderer_integration': False},
              'scope': 'Material constant and visible surface-assignment control only. No neural processing or faithful appearance/performance claim.',
              'next': 'Import original asymmetric BCR/NMO textures, verify rendered UV/material response, and calibrate light/exposure against the reference. Supported scene inputs/output remain separate.'}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes((json.dumps(result, indent=2, allow_nan=False) + '\n').encode('utf-8'))
    print(json.dumps({'verified': result['verified'], 'positive_control': response,
                      'regions': colors['region_mean_rgb8'], 'images': [white['image'], colors['image']]}))


if __name__ == '__main__':
    main()
