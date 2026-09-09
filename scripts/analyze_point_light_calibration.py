"""Check a predeclared engine/reference response mapping without fitting reserved data."""
import argparse
import itertools
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr import photometry, room_lights, room_textures
from enr.references import digest
from check_material_room import read_exr
from summarize_enfusion_room_geometry import import_trial
from summarize_enfusion_room_textures import trial as texture_trial

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path,data):path.write_bytes((json.dumps(data,indent=2,allow_nan=False)+'\n').encode('utf-8'))


def native_trial(path,load,built,provenance,plan,review):
    root=Path(path).resolve();result,image,config=texture_trial(root,load,built,provenance)
    report=read(root/'room.json');control=read(root/'light-control.json')
    if (control!=report['light_control'] or digest(root/'light-control.json')!=report['light_control_sha256']
            or control['plan']!=plan or control['plan_sha256']!=digest(ROOT/'scenes/point-light-calibration-v1.json')
            or control['requested']!=plan['cases'][control['case']] or result['case']!='packed'
            or control.get('clipping_followup') or config['hour']!=plan['hour']
            or config['dimensions']!=plan['dimensions']):
        raise ValueError('Native calibration plan differs')
    position=np.asarray(report['room_origin'])+plan['light']['local_position_enfusion_xyz']
    if not np.array_equal(position,control['world_position']):raise ValueError('Light position differs')
    run=root/'runs'/report['run_id'];log=(run/'console.log').read_text(encoding='utf-8')
    lines=[s.split('ENR_ROOM_LIGHT ',1)[1] for s in log.splitlines() if 'ENR_ROOM_LIGHT ' in s]
    if lines!=report['light_records']:raise ValueError('Native light records differ')
    matches=[r for r in review['frames'] if r['trial']==root.name]
    if (len(matches)!=1 or matches[0]['sha256']!=result['image']['sha256']
            or matches[0]['dimensions']!=plan['dimensions'] or not matches[0]['full_size_inspected']):
        raise ValueError('Missing hash-bound native image review')
    result.update(material_case=result.pop('case'),light_case=control['case'],light_control=control,
        native_light_readback=room_lights.check_readback(control,lines),light_records=lines,
        native_light_script_sha256=digest(run/'addon/Scripts/Game/ENR_RoomLight.c'),
        native_light_config_sha256=digest(run/'addon/Scripts/Game/ENR_RoomLightConfig.c'),
        visual_review=matches[0]['observation'])
    return result,image,config


def reference_data(root,plan):
    root=Path(root);record=read(root/'run.json')
    base=read(ROOT/plan['base_evidence'])
    if (record['status']!='succeeded' or record['operation']!='point-light-calibration-reference'
            or record['plan']!=plan or record['plan_sha256']!=digest(ROOT/'scenes/point-light-calibration-v1.json')
            or record['base_blend_sha256']!=base['source_artifacts']['blend_sha256']
            or record['base_config']!=base['render_run']['config'] or record['object_ids']!=base['render_run']['object_ids']
            or record['generator_sha256']!=digest(root/'generator.py')
            or record['base_evidence_sha256']!=digest(ROOT/plan['base_evidence'])
            or [r['role'] for r in record['renders']]!=plan['reference']['roles']):
        raise ValueError('Reference provenance differs')
    arrays={};data={}
    for render in record['renders']:
        role=render['role']
        for extension in ['exr','png']:
            if digest(root/(role+'.'+extension))!=render[extension+'_sha256']:raise ValueError('Reference output changed')
        bounces=plan['reference']['direct_max_bounces'] if role.startswith('direct') else plan['reference']['multibounce_max_bounces']
        seed=plan['reference']['seeds'][1 if role.endswith('_check') else 0]
        if (render['samples']!=plan['reference']['samples'] or render['seed']!=seed or render['max_bounces']!=bounces):
            raise ValueError('Reference sampling/transport differs')
        channels=read_exr(root/(role+'.exr'))
        arrays[role]=np.stack([channels['ViewLayer.Combined.'+c] for c in 'RGB'],axis=-1).astype(np.float64)
        if list(arrays[role].shape)!=[plan['dimensions'][1],plan['dimensions'][0],3]:raise ValueError('Reference size differs')
        data[role]=channels
    alignment={}
    for role in plan['reference']['roles'][1:]:
        alignment[role]={channel:bool(np.array_equal(data['direct'][channel],data[role][channel]))
            for channel in ['ViewLayer.Depth.Z','ViewLayer.Object Index.X']}
    if not all(alignment['multibounce'].values()):raise ValueError('Same-seed reference geometry passes differ')
    regions={}
    object_ids=data['direct']['ViewLayer.Object Index.X']
    for name,spec in plan['patches'].items():
        x0,y0,x1,y1=spec['xyxy'];expected=record['object_ids'][spec['object']]
        a=photometry.patch(arrays['direct'],spec['xyxy']);b=photometry.patch(arrays['direct_check'],spec['xyxy'])
        regions[name]={'expected_object':spec['object'],'object_fraction':float(np.mean(object_ids[y0:y1,x0:x1]==expected)),
            'direct_seed_relative_rmse':float(np.sqrt(np.mean((a-b)**2))/max(float(np.sqrt(np.mean(a*a))),1e-12)),
            'reference_mean_linear_rgb':a.mean(axis=(0,1)).tolist()}
    return record,arrays,alignment,regions


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--captures',nargs=8,required=True);p.add_argument('--reference',required=True)
    p.add_argument('--loaded-import',required=True);p.add_argument('--texture-build',required=True)
    p.add_argument('--review',required=True);p.add_argument('--out',required=True)
    p.add_argument('--fit-lock',required=True)
    a=p.parse_args();out=Path(a.out).resolve()
    if out.exists():raise ValueError('Choose a new analysis directory')
    plan=read(ROOT/'scenes/point-light-calibration-v1.json');review=read(a.review)
    load=import_trial(a.loaded_import);built,copies,provenance=room_textures.load_build(a.texture_build,ROOT)
    controls=[];images=[];configs=[]
    for path in a.captures:
        control,image,config=native_trial(path,load,built,provenance,plan,review)
        controls.append(control);images.append(image);configs.append(config)
    if ([c['light_case'] for c in controls]!=plan['runs'] or len({c['run_id'] for c in controls})!=8
            or any(c!=configs[0] for c in configs)
            or any(c['control']!=controls[0]['control'] for c in controls)):
        raise ValueError('Missing/duplicate capture or undeclared scene/config change')
    render,linear,alignment,regions=reference_data(a.reference,plan)
    first={}
    for control,image in zip(controls,images):first.setdefault(control['light_case'],image)
    lock=read(a.fit_lock)
    fit_inputs=[{'case':name,'run_id':next(c['run_id'] for c in controls if c['light_case']==name),
        'image_sha256':next(c['image']['sha256'] for c in controls if c['light_case']==name)} for name in plan['fit_cases']]
    if (lock['plan_sha256']!=digest(ROOT/'scenes/point-light-calibration-v1.json')
            or lock['reference_exr_sha256']!=next(r['exr_sha256'] for r in render['renders'] if r['role']=='direct')
            or lock['native_fit_inputs']!=fit_inputs or lock['photometry_sha256']!=digest(ROOT/'enr/photometry.py')
            or lock['reference_generator_sha256']!=render['generator_sha256']):
        raise ValueError('Frozen calibration inputs differ')
    repeated=photometry.fit_response(linear['direct'],first,plan)
    fit=lock['fit']
    if not np.allclose([fit['slope'],fit['intercept']],[repeated['slope'],repeated['intercept']],rtol=0,atol=1e-12):
        raise ValueError('Frozen calibration coefficients differ from declared fit')
    checks=[];whole=[]
    for name in plan['fit_cases']+plan['validation_cases']:
        gain=photometry.response_gain(fit,plan['cases'][name]['native_LV'])
        predicted=photometry.srgb_code(linear['direct'],gain)
        whole.append({'case':name,'rgb8_mae':float(np.abs(predicted-first[name]).mean()),'gain':gain})
        for label,spec in plan['patches'].items():
            source=photometry.patch(first[name],spec['xyxy']);target=photometry.patch(predicted,spec['xyxy'])
            delta=target-source
            limit=plan['calibration']['validation_fit_patch_mae_rgb8_max'] if spec['split']=='fit' else plan['calibration']['independent_patch_mae_rgb8_max']
            held_out=spec['split']=='validation' or name in plan['validation_cases']
            checks.append({'case':name,'patch':label,'held_out':held_out,'limit_rgb8_mae':limit,
                'mae_rgb8':float(np.abs(delta).mean()),'mean_channel_error_rgb8':delta.mean(axis=(0,1)).tolist(),
                'engine_mean_rgb8':source.mean(axis=(0,1)).tolist(),'predicted_mean_rgb8':target.mean(axis=(0,1)).tolist(),
                'passed':bool(np.abs(delta).mean()<=limit)})
    indices=[i for i,c in enumerate(controls) if c['light_case']=='lv10'];repeats=[]
    for left,right in itertools.combinations(indices,2):
        delta=np.abs(images[left]-images[right]);repeats.append({'before_run':controls[left]['run_id'],'after_run':controls[right]['run_id'],
            'mae_rgb8':float(delta.mean()),'maximum_rgb8':float(delta.max()),'exact_rgb_equal':bool(np.array_equal(images[left],images[right]))})
    off={name:float(photometry.patch(first['off'],spec['xyxy']).mean()) for name,spec in plan['patches'].items()}
    out.mkdir(parents=True,exist_ok=False);display=[]
    illustration=plan['calibration']['illustration_case'];gain=photometry.response_gain(fit,plan['cases'][illustration]['native_LV'])
    for role in plan['reference']['roles']:
        path=out/(role+'.png');pixels=np.rint(photometry.srgb_code(linear[role],gain)).astype(np.uint8)
        Image.fromarray(pixels,'RGB').save(path)
        display.append({'role':role,'file':path.name,'sha256':digest(path),'bytes':path.stat().st_size,
            'dimensions':plan['dimensions'],'reference_exr_sha256':next(r['exr_sha256'] for r in render['renders'] if r['role']==role),
            'gain':gain,'case':illustration,'transformation':'Declared scalar gain, clipped standard sRGB transfer, nearest-integer RGB8; no alignment, denoising or retouching'})
    gates={'reserved_response_checks':all(c['passed'] for c in checks if c['held_out']),
        'patch_object_identity':all(v['object_fraction']>=plan['calibration']['patch_object_fraction_min'] for v in regions.values()),
        'direct_reference_patch_noise':all(v['direct_seed_relative_rmse']<=plan['calibration']['direct_seed_patch_relative_rmse_max'] for v in regions.values()),
        'fit_patch_not_clipped':all(f['clipped_fraction']<=plan['calibration']['fit_patch_clipped_fraction_max'] for f in fit['fits'])}
    noise={}
    for role in ['direct','multibounce']:
        primary=np.asarray(Image.open(out/(role+'.png')),dtype=np.float64)
        check=np.asarray(Image.open(out/(role+'_check.png')),dtype=np.float64)
        noise[role]={'display_seed_mae_rgb8':float(np.abs(primary-check).mean()),'display_seed_max_rgb8':float(np.abs(primary-check).max())}
    result={'schema_version':1,'operation':'point-light-calibration','evidence_verification':'succeeded',
        'plan':plan,'plan_sha256':digest(ROOT/'scenes/point-light-calibration-v1.json'),
        'analyzer_sha256':digest(__file__),'photometry_sha256':digest(ROOT/'enr/photometry.py'),
        'light_readback_parser_sha256':digest(ROOT/'enr/room_lights.py'),'review_sha256':digest(a.review),
        'loaded_import':load,'texture_build':provenance,'controls':controls,'capture_config':configs[0],
        'reference':render,'reference_report_sha256':digest(Path(a.reference)/'run.json'),
        'reference_geometry_alignment':alignment,'reference_regions':regions,'reference_display_noise':noise,
        'fit':fit,'fit_lock':lock,'fit_lock_sha256':digest(a.fit_lock),'patch_checks':checks,'whole_image_diagnostics':whole,'off_patch_means_rgb8':off,
        'repeat_pairs':repeats,'display_outputs':display,'gates':gates,
        'verified':{'calibration_candidate_passed':all(gates.values()),
            'all_signed_native_readbacks_match':all(c['native_light_readback']['all_readbacks_match'] for c in controls),
            'native_validations_and_captures':True,'reserved_data_excluded_from_fit':True,
            'reference_pair_geometry_identical':True,'aligned_enfusion_appearance_pair':False,'renderer_integration':False},
        'scope':plan['scope'],'limits':plan['limits']+['A passing patch response model would not prove full-image material or shadow equivalence. All full-image errors are retained.',
            'The role named direct permits one bounce and visibly retains indirect illumination; it is a limited-bounce baseline, not a direct-light-only isolation.',
            'The disabled native radius remains -15 against a requested +15. Requested intensity/color/clipping have no getter verification.']}
    write(out/'analysis.json',result)
    print(json.dumps({'fit':fit,'gates':gates,'reference_regions':regions,'patch_checks':checks,'whole':whole,'noise':noise,'repeats':repeats}))


if __name__=='__main__':main()
