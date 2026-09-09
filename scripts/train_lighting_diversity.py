"""Fit equal-budget lighting variants; lock validation selection before test access."""
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np

from lighting_diversity_data import ROOT,sha,write,load_case
from enr import lighting,diversity


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();root=Path(a.root).resolve();out=Path(a.out).resolve()
    run=json.loads((root/'run.json').read_text());plan=json.loads((ROOT/'scenes/lighting-diversity-v1.json').read_text())
    diversity.validate_fit_run(run,plan)
    if run['plan_sha256']!=sha(ROOT/'scenes/lighting-diversity-v1.json'):raise ValueError('Changed plan')
    out.mkdir(parents=True,exist_ok=False)
    report={'status':'running','schema_version':1,'plan_sha256':run['plan_sha256'],'renderer_run_sha256':sha(root/'run.json'),
            'trainer_sha256':sha(__file__),'loader_sha256':sha(ROOT/'scripts/lighting_diversity_data.py'),
            'model_code_sha256':sha(ROOT/'enr/lighting.py'),'split_code_sha256':sha(ROOT/'enr/diversity.py'),
            'training':plan['training'],'python':sys.version,'numpy':np.__version__,'models':{},'sample_records':[],
            'test_accessed':False,'scene_groups':{split:[s['group'] for s in plan['scenes'] if s['split']==split] for split in ('train','validation')},
            'controls':'Identical pixel indices, minibatch RNG seed, optimizer step count and checkpoint schedule; no test data loaded'}
    def save():write(out/'run.json',report)
    save()
    try:
        pools={'train':[],'validation':[]};rng=np.random.default_rng(plan['training']['seed'])
        for case in run['cases']:
            d=load_case(root,run,case);candidates=np.flatnonzero(d['valid'])
            ids=rng.choice(candidates,min(len(candidates),plan['training']['pixels_per_case']),replace=False)
            path=out/(case['id']+'-pixels.npy');np.save(path,ids)
            pools[case['split']].append((d['x'].reshape(-1,20)[ids],d['y'].reshape(-1,3)[ids]))
            report['sample_records'].append({'case':case['id'],'group':case['group'],'split':case['split'],'count':len(ids),
                                              'indices_sha256':sha(path),'geometry':d['geometry']})
            save();print('ENR_POOL '+case['id'],flush=True)
        tx,ty=(np.concatenate([v[i] for v in pools['train']]) for i in range(2))
        vx,vy=(np.concatenate([v[i] for v in pools['validation']]) for i in range(2))
        report.update(training_pixels=len(tx),validation_pixels=len(vx));lock_models={}
        for name in ('scene','relative','rgb'):
            start=time.perf_counter()
            model=lighting.fit(diversity.select(tx,name),ty,diversity.select(vx,name),vy,plan['training'],
                               lambda item:print(json.dumps({'model':name,**item}),flush=True))
            elapsed=time.perf_counter()-start;path=out/(name+'-model.json')
            metadata={'plan_sha256':run['plan_sha256'],'scene_groups':report['scene_groups'],
                      'selected_step':model['selected_step'],'seed':plan['training']['seed'],'test_accessed':False}
            lighting.save(path,model,metadata,feature_names=diversity.names(name))
            restored,record=lighting.load(path)
            if not np.array_equal(lighting.predict(diversity.select(vx[:32],name),model),lighting.predict(diversity.select(vx[:32],name),restored)):
                raise ValueError('Model roundtrip changes predictions')
            val=float(np.mean((lighting.predict(diversity.select(vx,name),restored)-vy)**2))
            report['models'][name]={'file':path.name,'sha256':sha(path),'features':record['features'],
                                    'parameters':sum(v.size for v in model['weights'].values()),'training_seconds':elapsed,
                                    'selected_step':model['selected_step'],'validation_mse':val,'history':model['history']}
            lock_models[name]={'file':path.name,'sha256':sha(path)};save()
        for name,columns in [('affine-scene',list(range(20))),('affine-rgb',list(range(3)))]:
            design=np.column_stack([tx[:,columns],np.ones(len(tx))]).astype(np.float64)
            regularizer=np.eye(design.shape[1])*1e-3;regularizer[-1,-1]=0
            weights=np.linalg.solve(design.T@design+regularizer,design.T@ty)
            path=out/(name+'.json');write(path,{'columns':columns,'weights':weights.tolist(),'residual_limit':lighting.LIMIT,'plan_sha256':run['plan_sha256']})
            lock_models[name]={'file':path.name,'sha256':sha(path)}
        candidate=diversity.choose_candidate(report['models']);report['selected_candidate']=candidate
        report['status']='succeeded';save()
        write(out/'model-lock.json',{'schema_version':1,'plan_sha256':run['plan_sha256'],'fit_report_sha256':sha(out/'run.json'),
                                     'training_complete':True,'test_accessed':False,'selected_candidate':candidate,'models':lock_models,
                                     'selection_rule':plan['selection']})
        print(json.dumps({'selected_candidate':candidate,'models':{k:{q:v for q,v in m.items() if q!='history'} for k,m in report['models'].items()}},indent=2))
    except Exception:report['status']='failed';save();raise


if __name__=='__main__':main()
