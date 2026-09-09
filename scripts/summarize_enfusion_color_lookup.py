"""Bind native lookup controls, full-size reviews and all display diagnostics."""
import argparse
import itertools
import json
from pathlib import Path
import re
import sys

import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr import sequence,color_lookup
from enr.references import digest


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def checked_run(root,name,expected_hash,command,status='succeeded'):
    if not re.fullmatch(r'[0-9]{8}T[0-9]{6}-[a-f0-9]{10}',name):raise ValueError('Invalid run identity')
    path=root/'runs'/name/'run.json';run=read(path)
    if digest(path)!=expected_hash or run['command']!=command or run['status']!=status:raise ValueError('Run changed or incomplete')
    return path.parent,run


def metrics(a,b):
    delta=np.abs(np.asarray(a,dtype=np.float64)-np.asarray(b,dtype=np.float64))
    return {'rgb8_mae':float(delta.mean()),'rgb8_rmse':float(np.sqrt(np.square(delta).mean())),
            'max_abs_rgb8':float(delta.max()),'exact_rgb_equal':bool(np.array_equal(a,b))}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['batch','build','schema','inventory','failed-inventory','prior-off','prior-identity','review','out']:p.add_argument('--'+name,required=True)
    a=p.parse_args();out=Path(a.out)
    if out.exists():raise ValueError('Choose a new portable report')
    build,_,provenance=color_lookup.load_build(a.build,ROOT);plan=build['plan']
    followup=read(ROOT/'scenes/color-lookup-priority-v2.json');followup_hash=digest(ROOT/'scenes/color-lookup-priority-v2.json')
    batch_path=Path(a.batch);batch=read(batch_path);review=read(a.review)
    if batch['status']!='succeeded' or [v['case'] for v in batch['runs']]!=followup['runs'] or len(batch['runs'])!=7:raise ValueError('Incomplete batch')
    if len(review['frames'])!=9 or len({v['trial'] for v in review['frames']})!=9:raise ValueError('Inspect all nine retained images')
    reviewed={v['trial']:v for v in review['frames']};controls=[];images=[];configs=[]
    for trial in batch['runs']:
        root=(batch_path.parent/trial['root']).resolve()
        if root.parent!=batch_path.parent.resolve() or trial['exit_code']!=0:raise ValueError('Invalid trial path or exit')
        r=read(root/'lookup-capture.json');folder,native=checked_run(root,r['run_id'],r['capture_manifest_sha256'],'capture')
        _,validation=checked_run(root,r['validation_run'],r['validation_manifest_sha256'],'validate')
        config=read(root/'capture-config.json')
        if validation['process_exit_code']!=0 or r['config_sha256']!=digest(root/'capture-config.json') or r['driver_sha256']!=digest(root/'capture_driver.py'):raise ValueError('Trial provenance changed')
        if r['build']!=provenance or r['plan_sha256']!=build['plan_sha256'] or r['followup']!={'plan':followup,'sha256':followup_hash}:raise ValueError('Trial plan/build differs')
        recomputed=sequence.verify(config,dict(native,directory=str(folder)))
        if recomputed['frames']!=r['frames'] or r['case']!=trial['case']:raise ValueError('Frame provenance differs')
        if digest(folder/'console.log')!=r['console_sha256']:raise ValueError('Console changed')
        log=(folder/'console.log').read_text(encoding='utf-8')
        records=[v.split('ENR_LOOKUP ',1)[1] for v in log.splitlines() if 'ENR_LOOKUP ' in v]
        check=color_lookup.check_requests(records,r['selected_material']['table'],r['case'],followup['priority'],followup['expected_table_raw_suffix'],log)
        if records!=r['lookup_records'] or check!=r['request_checks'] or not check['passed'] or r['control_status']!='succeeded':raise ValueError('Native request check failed or changed')
        frame=r['frames'][0];path=folder/frame['file'];inspected=reviewed[root.name]
        with Image.open(path) as im: dimensions=list(im.size);pixels=np.asarray(im.convert('RGB')).copy()
        if not inspected['full_size_inspected'] or inspected['sha256']!=digest(path) or inspected['sha256']!=frame['sha256'] or inspected['dimensions']!=dimensions:raise ValueError('Review does not bind the native image')
        controls.append({'trial':root.name,'case':r['case'],'run_id':r['run_id'],'validation_run':r['validation_run'],
                         'report_sha256':digest(root/'lookup-capture.json'),'capture_manifest_sha256':r['capture_manifest_sha256'],
                         'validation_manifest_sha256':r['validation_manifest_sha256'],'console_sha256':r['console_sha256'],
                         'driver_sha256':r['driver_sha256'],'addon_sha256':r['addon_sha256'],
                         'image':{'file':frame['file'].replace('\\','/'),'sha256':frame['sha256'],'dimensions':dimensions,'bytes':path.stat().st_size},
                         'camera':frame['camera'],'projection':frame['projection'],'request_checks':check,'lookup_records':records,'selected_material':r['selected_material']})
        images.append(pixels);configs.append(config)
    if any(c!=configs[0] for c in configs) or len({v['run_id'] for v in controls})!=7:raise ValueError('Configs differ or duplicate runs')
    first={}
    for c,im in zip(controls,images):first.setdefault(c['case'],im)
    source=first['off'];predictions={'identity':source,'inversion':255-source,'constant':np.broadcast_to(plan['constant_rgb8'],source.shape),'removed':source}
    displays={case:metrics(first[case],expected) for case,expected in predictions.items()}
    response={case:metrics(first[case],source) for case in predictions}
    constant=first['constant']
    indices=[i for i,c in enumerate(controls) if c['case']=='off']
    repeats=[{'before_run':controls[l]['run_id'],'after_run':controls[r]['run_id'],**metrics(images[l],images[r])} for l,r in itertools.combinations(indices,2)]
    # Keep the two initial captures, including the explicit priority rejection.
    prior=[]
    for raw_root,case in [(a.prior_off,'off'),(a.prior_identity,'identity')]:
        root=Path(raw_root).resolve();runs=[(f,read(f)) for f in (root/'runs').glob('*/run.json')]
        captures=[(f,r) for f,r in runs if r['command']=='capture'];validations=[(f,r) for f,r in runs if r['command']=='validate']
        if len(captures)!=1 or len(validations)!=1:raise ValueError('Unexpected prior runs')
        manifest,native=captures[0];vpath,validation=validations[0];folder=manifest.parent
        if native['status']!='succeeded' or validation['status']!='succeeded' or validation['process_exit_code']!=0:raise ValueError('Prior native operations incomplete')
        frame=sequence.verify(read(root/'capture-config.json'),dict(native,directory=str(folder)))['frames'][0]
        path=folder/frame['file'];inspected=reviewed[root.name]
        if inspected['sha256']!=digest(path) or inspected['sha256']!=frame['sha256'] or not inspected['full_size_inspected'] or inspected['dimensions']!=[2560,1440]:raise ValueError('Prior review mismatch')
        log=(folder/'console.log').read_text(encoding='utf-8');records=[v.split('ENR_LOOKUP ',1)[1] for v in log.splitlines() if 'ENR_LOOKUP ' in v]
        rejections=[v.strip() for v in log.splitlines() if 'Cannot set ColorGradingEffect' in v]
        if case=='identity' and (len(rejections)!=1 or 'priority 1000, max available is 19' not in rejections[0]):raise ValueError('Retained priority rejection differs')
        prior.append({'trial':root.name,'case':case,'run_id':native['run_id'],'capture_manifest_sha256':digest(manifest),
                      'validation_manifest_sha256':digest(vpath),'console_sha256':digest(folder/'console.log'),'driver_sha256':digest(root/'capture_driver.py'),
                      'image':{'file':frame['file'].replace('\\','/'),'sha256':frame['sha256'],'dimensions':[2560,1440],'bytes':path.stat().st_size},
                      'lookup_records':records,'engine_rejections':rejections,'effect_control_passed':False,
                      'scope':'Initial priority-1000 batch stops after rejected identity; remaining five cases were not launched'})
    schema_root=Path(a.schema);schema=read(schema_root/'schema.json');sf,srun=checked_run(schema_root,schema['run_id'],schema['manifest_sha256'],'material-schema')
    _,sval=checked_run(schema_root,schema['validation_run'],schema['validation_manifest_sha256'],'validate')
    for name,key in [('console.log','console_sha256'),('driver.py','driver_sha256'),('addon/Scripts/WorkbenchGame/ENR_MaterialSchemaPlugin.c','plugin_sha256')]:
        if digest(sf/name)!=schema[key]:raise ValueError('Schema snapshot changed')
    if srun['process_exit_code']!=0 or srun['terminated_owned_process'] or sval['process_exit_code']!=0:raise ValueError('Schema did not exit naturally')
    if schema['plan_sha256']!=digest(ROOT/'scenes/color-lookup-schema-v1.json'):raise ValueError('Schema plan changed')
    schema_records=[v.split('ENR_SCHEMA',1)[1] for v in (sf/'console.log').read_text().splitlines() if 'ENR_SCHEMA' in v]
    if schema_records!=schema['records']:raise ValueError('Schema records changed')
    inventory=read(Path(a.inventory)/'resources.json');inventory_folder=Path(a.inventory)/'runs'/inventory['inventory_run']
    if digest(inventory_folder/'console.log')!=inventory['console_sha256'] or schema['inventory']['report_sha256']!=digest(Path(a.inventory)/'resources.json'):raise ValueError('Inventory differs')
    failed=read(Path(a.failed_inventory)/'resources.json');ff,fr=checked_run(Path(a.failed_inventory),failed['inventory_run'],failed['inventory_manifest_sha256'],'resource-inventory','failed')
    if digest(ff/'console.log')!=failed['console_sha256']:raise ValueError('Failed inventory changed')
    counts=[v.split('ENR_RESOURCE_DONE ',1)[1] for v in inventory['records'] if 'ENR_RESOURCE_DONE ' in v]
    inventory_summary={'run_id':inventory['inventory_run'],'report_sha256':digest(Path(a.inventory)/'resources.json'),'console_sha256':inventory['console_sha256'],'query_outcomes':counts,
                       'initial_failure':{'run_id':fr['run_id'],'manifest_sha256':digest(ff/'run.json'),'process_exit_code':fr['process_exit_code'],'error':fr.get('error'),'records':failed['records']}}
    positive=response['constant']['rgb8_mae']>=plan['positive_control']['minimum_rgb8_mae_vs_first_off']
    result={'schema_version':1,'operation':'color-lookup-characterization','evidence_verification':'succeeded',
            'plan':plan,'plan_sha256':build['plan_sha256'],'followup':followup,'followup_sha256':followup_hash,
            'summarizer_sha256':digest(__file__),'lookup_verifier_sha256':digest(ROOT/'enr/color_lookup.py'),
            'inventory':inventory_summary,'material_schema':schema,'build':build,'build_verification':provenance,
            'controls':controls,'capture_config':configs[0],'prior_controls':prior,'visual_review':review,'visual_review_sha256':digest(a.review),
            'cpu_display_hypothesis_errors':displays,'changes_vs_first_off':response,'off_repeat_pairs':repeats,
            'constant_observed_rgb8':{'mean':constant.mean(axis=(0,1)).tolist(),'min':constant.min(axis=(0,1)).tolist(),'max':constant.max(axis=(0,1)).tolist()},
            'verified':{'native_material_schema':True,'original_volume_pixels':True,'all_followup_request_checks':True,
                        'constant_positive_response':positive,'exact_display_mapping':all(v['exact_rgb_equal'] for v in displays.values()),
                        'full_lighting_model':False,'scene_buffers':False,'renderer_integration':False,'motion_fidelity':False,'complete_frame_performance':False},
            'limits':plan['limits']+followup['limits']+['This first characterization has no reserved color-accuracy gate. All identity/inversion/constant/removal errors and all off pairs are retained.']}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes((json.dumps(result,indent=2,allow_nan=False)+'\n').encode())
    print(json.dumps({'verified':result['verified'],'errors':displays,'constant':result['constant_observed_rgb8'],'repeats':repeats}))


if __name__=='__main__':main()
