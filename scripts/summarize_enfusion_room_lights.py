"""Verify original room point-light response, independent repeats and clip control."""
import argparse
import itertools
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr import room_lights, room_textures
from enr.references import digest
from summarize_enfusion_room_geometry import import_trial
from summarize_enfusion_room_textures import read, trial as texture_trial


def trial(path, load, built, provenance, plan, review):
    root = Path(path).resolve()
    result, image, config = texture_trial(root, load, built, provenance)
    report = read(root / 'room.json')
    control = read(root / 'light-control.json')
    if (control != report['light_control'] or digest(root / 'light-control.json') != report['light_control_sha256']
            or control['plan'] != plan or control['plan_sha256'] != digest(ROOT / 'scenes/material-room-light-control-v1.json')
            or control['requested'] != plan['cases'][control['case']] or result['case'] != plan['texture_case']
            or config['hour'] != plan['hour']):
        raise ValueError('Light plan/capture binding differs')
    expected_position = np.asarray(report['room_origin']) + plan['light']['local_position_enfusion_xyz']
    if not np.array_equal(expected_position, control['world_position']):
        raise ValueError('Light position differs from original room coordinates')
    run = root / 'runs' / report['run_id']
    log = (run / 'console.log').read_text(encoding='utf-8')
    lines = [line.split('ENR_ROOM_LIGHT ', 1)[1] for line in log.splitlines() if 'ENR_ROOM_LIGHT ' in line]
    if lines != report['light_records']:
        raise ValueError('Light records differ from native log')
    native_readback = room_lights.check_readback(control, lines)
    followup = control.get('clipping_followup')
    if followup:
        clip_path = ROOT / 'scenes/material-room-light-clip-control-v1.json'
        if (followup['plan'] != read(clip_path) or followup['plan_sha256'] != digest(clip_path)
                or followup['base_plan_sha256'] != control['plan_sha256']
                or followup['plan']['base_case'] != control['case']):
            raise ValueError('Clipping follow-up differs from its separate plan')
    matches = [r for r in review['frames'] if r['trial'] == root.name]
    if (len(matches) != 1 or matches[0]['sha256'] != result['image']['sha256']
            or matches[0]['dimensions'] != report['dimensions'] or not matches[0]['full_size_inspected']):
        raise ValueError('Missing hash-bound full-size visual inspection')
    means = {}
    for name, (x0,y0,x1,y1) in plan['regions_xyxy'].items():
        if not (0 <= x0 < x1 <= image.shape[1] and 0 <= y0 < y1 <= image.shape[0]):
            raise ValueError('Region outside capture')
        means[name] = {'mean_rgb8': float(image[y0:y1,x0:x1].mean()),
                       'channels_rgb8': image[y0:y1,x0:x1].mean(axis=(0,1)).tolist()}
    result.update(material_case=result.pop('case'), light_case=control['case'], light_control=control,
                  light_records=lines, native_light_readback=native_readback,
                  native_light_script_sha256=digest(run / 'addon/Scripts/Game/ENR_RoomLight.c'),
                  native_light_config_sha256=digest(run / 'addon/Scripts/Game/ENR_RoomLightConfig.c'),
                  region_means=means, full_mean_rgb8=float(image.mean()),
                  visual_review=matches[0]['observation'])
    return result, image, config


def difference(a, b, regions):
    if a.shape != b.shape:
        raise ValueError('Capture dimensions differ')
    delta=np.abs(a-b)
    return {'full_rgb8_mae':float(delta.mean()), 'full_max_abs_rgb8':float(delta.max()),
            'regions_rgb8_mae':{name:float(delta[y0:y1,x0:x1].mean()) for name,(x0,y0,x1,y1) in regions.items()},
            'exact_rgb_equal':bool(np.array_equal(a,b))}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures', nargs=5, required=True, help='Off, low and three independent high cases in declared order')
    parser.add_argument('--clip-capture', required=True)
    parser.add_argument('--loaded-import', required=True)
    parser.add_argument('--texture-build', required=True)
    parser.add_argument('--review', required=True)
    parser.add_argument('--out', required=True)
    args=parser.parse_args()
    out=Path(args.out)
    if out.exists():
        raise ValueError('Choose a new portable report path')
    plan=read(ROOT/'scenes/material-room-light-control-v1.json')
    load=import_trial(args.loaded_import)
    built, copies, provenance=room_textures.load_build(args.texture_build, ROOT)
    review=read(args.review)
    controls,images,configs=[],[],[]
    for path in args.captures + [args.clip_capture]:
        control,image,config=trial(path,load,built,provenance,plan,review)
        controls.append(control); images.append(image); configs.append(config)
    if ([c['light_case'] for c in controls[:5]] != plan['runs']
            or any(c['light_control'].get('clipping_followup') for c in controls[:5])
            or not controls[-1]['light_control'].get('clipping_followup')
            or any(c != configs[0] for c in configs)
            or len({c['run_id'] for c in controls}) != 6
            or any(c['control'] != controls[0]['control'] for c in controls)):
        raise ValueError('Missing/duplicate cases or non-light capture inputs differ')
    gate=plan['response_gate']; region=gate['region']
    means=[c['region_means'][region]['mean_rgb8'] for c in controls]
    response={'region':region,'high_minus_off_rgb8':means[2]-means[0], 'high_minus_low_rgb8':means[2]-means[1],
              'limits':gate,
              'passed':means[2]-means[0] > gate['mean_rgb8_high_minus_off_min'] and means[2]-means[1] > gate['mean_rgb8_high_minus_low_min']}
    repeats=[]
    for a,b in itertools.combinations(range(2,5),2):
        repeats.append(dict(difference(images[a],images[b],plan['regions_xyxy']), before_run=controls[a]['run_id'],after_run=controls[b]['run_id']))
    clip=controls[-1]['light_control']['clipping_followup']['plan']
    clip_delta=controls[-1]['region_means'][clip['region']]['mean_rgb8']-controls[1]['region_means'][clip['region']]['mean_rgb8']
    followup={'plan':clip,'difference':difference(images[1],images[-1],plan['regions_xyxy']),
              'region_mean_increase_rgb8':clip_delta,'passed':clip_delta > clip['minimum_mean_rgb8_increase_vs_original_low'],
              'selection':'Separate follow-up chosen after observing no region response at LV10 and a clear response at LV12'}
    result={'schema_version':1,'operation':'original-room-point-light-control','evidence_verification':'succeeded',
            'summarizer_sha256':digest(__file__),'readback_parser_sha256':digest(ROOT/'enr/room_lights.py'),
            'plan':plan,'plan_sha256':digest(ROOT/'scenes/material-room-light-control-v1.json'),
            'loaded_import':load,'texture_build':provenance,'controls':controls,
            'review_sha256':digest(args.review),'positive_response':response,
            'off_vs_low':difference(images[0],images[1],plan['regions_xyxy']),
            'high_repeat_pairs':repeats,'clipping_followup':followup,
            'verified':{'native_compile_and_capture':True,'unchanged_geometry_materials_camera_environment_exposure':True,
                        'all_signed_native_readbacks_match':all(c['native_light_readback']['all_readbacks_match'] for c in controls),
                        'high_light_positive_response':response['passed'],'clip_bias_positive_response':followup['passed'],
                        'three_independent_high_captures':True,'radiometric_calibration':False,
                        'isolated_environment':False,'aligned_appearance_pair':False,'renderer_integration':False},
            'scope':'Scripted point-light fixture and static repeat controls. No neural processing or performance measurement.',
            'limits':plan['limits']+['Disabled GetRadius returns -15 for requested +15; raw mismatch remains visible.',
                'Light color/LV, attenuation and clipping bias are requested calls without native getter verification.',
                'Static repeats do not establish motion stability or presentation synchronization.',
                'Hard black shadows and coarse/mottled reflection edges remain visible; no physical material match is claimed.'],
            'next':'Use a confirmed light-clipping policy, then calibrate exposure/color and a point-light reference pair. Environment, roughness and supported neural scene inputs/output remain open.'}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes((json.dumps(result,indent=2,allow_nan=False)+'\n').encode('utf-8'))
    print(json.dumps({'verified':result['verified'],'positive_response':response,'repeat_pairs':repeats,'clipping_followup':followup}))


if __name__=='__main__':
    main()
