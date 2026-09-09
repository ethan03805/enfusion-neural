"""Evaluate locked variants on untouched test motion and published regressions.

No training, checkpoint selection or threshold adjustment is performed here.
"""
import argparse
import json
from pathlib import Path
import time
import numpy as np

from lighting_diversity_data import ROOT,sha,write,load_case,metric
from evaluate_lighting_motion import load_frame as load_regression
from enr import lighting,diversity,temporal


def marking_contrast(value,ids,objects):
    if 'mark-board' not in objects:return None
    board=ids==objects['mark-board']['id']
    bars=np.isin(ids,[o['id'] for n,o in objects.items() if n.startswith('mark-bar-')])
    if not board.any() or not bars.any():return None
    value=np.log1p(value)@np.array([.2126,.7152,.0722])
    return float(value[board].mean()-value[bars].mean())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--test-root',required=True);p.add_argument('--models',required=True)
    p.add_argument('--regression-root',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();test_root=Path(a.test_root).resolve();model_root=Path(a.models).resolve();old_root=Path(a.regression_root).resolve();out=Path(a.out).resolve()
    test=json.loads((test_root/'run.json').read_text());plan=json.loads((ROOT/'scenes/lighting-diversity-v1.json').read_text())
    diversity.validate_plan(plan);lock_path=model_root/'model-lock.json';lock=json.loads(lock_path.read_text())
    if test['status']!='succeeded' or test['phase']!='test' or test['plan']!=plan or test['plan_sha256']!=sha(ROOT/'scenes/lighting-diversity-v1.json'):
        raise ValueError('Incomplete or changed test definition')
    if test['model_lock_sha256']!=sha(lock_path) or lock['test_accessed'] or not lock['training_complete']:
        raise ValueError('Test did not follow a frozen validation selection')
    models={};affines={}
    for name,entry in lock['models'].items():
        path=model_root/entry['file']
        if sha(path)!=entry['sha256']:raise ValueError('Locked model changed')
        if name.startswith('affine'):affines[name]=json.loads(path.read_text())
        else:
            models[name],record=lighting.load(path)
            if record['features']!=diversity.names(name):raise ValueError('Model feature identity changed')
    old=json.loads((old_root/'run.json').read_text())
    if old['status']!='succeeded' or old['plan_sha256']!=sha(ROOT/'scenes/lighting-motion-v1.json'):raise ValueError('Invalid regression run')
    if len(old['sequences'])!=len(old['plan']['sequences']):raise ValueError('Missing regression sequence')
    for name,definition in old['plan']['models'].items():
        path=ROOT/definition['path']
        if sha(path)!=definition['sha256']:raise ValueError('Frozen regression control changed')
        models['old-'+name]=lighting.load(path)[0]
    out.mkdir(parents=True,exist_ok=False)
    report={'schema_version':1,'status':'running','plan':plan,'plan_sha256':test['plan_sha256'],
            'renderer_run_sha256':sha(test_root/'run.json'),'regression_run_sha256':sha(old_root/'run.json'),
            'model_lock':lock,'model_lock_sha256':sha(lock_path),'evaluator_sha256':sha(__file__),
            'temporal_code_sha256':sha(ROOT/'enr/temporal.py'),'model_code_sha256':sha(ROOT/'enr/lighting.py'),
            'selected_candidate':lock['selected_candidate'],'training_performed':False,'selection_performed':False,
            'rendering':test,'regression_rendering':old,'sequences':[],'cases':[]}
    def save():write(out/'run.json',report)
    save()
    try:
        definition=next(s for s in plan['scenes'] if s['split']=='test');motion=plan['test_sequence']
        if len(test['cases'])!=motion['frames'] or set(test['scenes'])!={definition['id']}:raise ValueError('Missing/unplanned test frames')
        path_plan={**motion,'camera_target':plan['camera_target']}
        temporal.validate_sequence({'id':definition['id'],'frames':test['cases']},{'id':definition['id']},path_plan)
        sequences=[(definition['id'],'test',test['cases'],test['scenes'][definition['id']],plan['evaluation_samples'])]
        for s,d in zip(old['sequences'],old['plan']['sequences']):
            temporal.validate_sequence(s,d,old['plan'])
            sequences.append((s['id'],'regression',s['frames'],s,old['plan']['samples']))
        for seq,split,cases,scene,samples in sequences:
            summary={'id':seq,'split':split,'frames':len(cases),'samples':samples,'playback_fps':20,
                     'publication_frame':motion['publication_frame'] if split=='test' else old['plan']['publication_frame']}
            report['sequences'].append(summary);previous=None
            for case in cases:
                index=case['index']
                if split=='test':
                    d=load_case(test_root,test,case);d['paired']=d['target'];d['target']=d['independent'];folder=test_root/case['id']
                else:
                    folder=old_root/seq/f'{index:04d}';d=load_regression(folder,case,scene,old['plan'])
                x=d['x'].reshape(-1,20);base=np.log1p(d['rgb']);predictions={'source':d['rgb'].copy()};timings={}
                for name,affine in affines.items():
                    residual=np.column_stack([x[:,affine['columns']],np.ones(len(x))])@np.asarray(affine['weights'])
                    predictions[name]=np.maximum(np.expm1(base+np.clip(residual,-lighting.LIMIT,lighting.LIMIT).reshape(base.shape)),0)
                for name,model in models.items():
                    variant=name.removeprefix('old-')
                    start=time.perf_counter();residual=lighting.predict(diversity.select(x,variant),model).reshape(base.shape)
                    predictions[name]=np.maximum(np.expm1(base+residual),0);timings[name]=(time.perf_counter()-start)*1000
                for value in predictions.values():value[~d['valid']]=d['rgb'][~d['valid']]
                ids=d['ids'];objects=scene['objects']
                masks={'all':None,'object_edges':(ids>0)&~temporal.interior(ids),
                       'thin_posts':np.isin(ids,[o['id'] for n,o in objects.items() if n.startswith('post-')]),
                       'markings':np.isin(ids,[o['id'] for n,o in objects.items() if n.startswith('mark-')])}
                entry={'id':seq+f'-{index:04d}','sequence':seq,'split':split,'index':index,'geometry':d['geometry'],
                       'raw_source_png_sha256':sha(folder/'source.png'),'raw_reference_png_sha256':sha(folder/'independent.png'),
                       'raw_folder':str(folder),'cpu_inference_ms_excludes_features_and_io':timings,'outputs':{},
                       'metrics':{name:{region:metric(value,d['target'],mask) if mask is None or mask.any() else None for region,mask in masks.items()} for name,value in predictions.items()},
                       'paired_reference_metrics':{name:metric(value,d['paired']) for name,value in predictions.items()},
                       'reference_seed_difference':metric(d['paired'],d['target']),
                       'marking_contrast':{name:marking_contrast(value,ids,objects) for name,value in {**predictions,'reference':d['target'],'paired':d['paired']}.items()}}
                errors={name:np.log1p(value)-np.log1p(d['target']) for name,value in predictions.items()}
                paired_errors={name:np.log1p(value)-np.log1p(d['paired']) for name,value in predictions.items()}
                errors['reference_noise']=np.log1p(d['paired'])-np.log1p(d['target'])
                if previous is not None:
                    xy,mask,coverage=temporal.correspondence(d,previous,previous['camera_matrix'],plan['vertical_fov_degrees'])
                    if coverage['valid_pixels']<1000 or coverage['valid_fraction']<.1:raise ValueError('Insufficient temporal coverage')
                    entry['temporal']={'coverage':coverage,'error_change':{n:temporal.error_change(e,previous['errors'][n],xy,mask) for n,e in errors.items()},
                                      'paired_error_change':{n:temporal.error_change(e,previous['paired_errors'][n],xy,mask) for n,e in paired_errors.items()}}
                    unmatched=temporal.interior(ids)&~mask
                    entry['unmatched_interior_metrics']={n:metric(v,d['target'],unmatched) if unmatched.any() else None for n,v in predictions.items()}
                destination=out/entry['id'];destination.mkdir()
                for name,value in {**predictions,'reference':d['target']}.items():
                    path=destination/(name+'.npy');np.save(path,np.concatenate([value,d['alpha'][...,None]],-1).astype(np.float32))
                    entry['outputs'][name]={'linear_rgba_sha256':sha(path)}
                previous={k:d[k] for k in ('position','normal','ids')};previous.update(camera_matrix=case['camera_matrix'],errors=errors,paired_errors=paired_errors)
                report['cases'].append(entry);save();print('ENR_DIVERSITY_EVALUATED '+entry['id'],flush=True)
        report['status']='succeeded'
    except Exception:report['status']='failed';raise
    finally:save()


if __name__=='__main__':main()
