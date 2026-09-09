"""Run the locked full lighting model on every retained test/regression frame.

Reuses existing source passes and frozen CPU controls; no rendering or training.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np

from lighting_gpu_run import ROOT,locked_models,run,write
from lighting_diversity_data import load_case,metric
from evaluate_lighting_motion import load_frame
from evaluate_lighting_diversity import marking_contrast
from summarize_lighting_diversity import summarize
from enr import lighting_gpu,temporal
from enr.references import digest


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('test-root','test-cpu','regression-root','regression-cpu','out'):p.add_argument('--'+name,required=True)
    p.add_argument('--exe',default='build/Release/enr_gpu.exe');a=p.parse_args()
    out=Path(a.out).resolve()
    if not out.is_relative_to((ROOT/'experiments/local').resolve()):raise ValueError('Use a dedicated local experiment output')
    out.mkdir(parents=True,exist_ok=False)
    models,binding=locked_models();model=models['scene'];gpu_plan=binding['plan'];sequences=[]
    provenance={}
    for split,raw,cpu,evidence in [('test',a.test_root,a.test_cpu,'evidence/lighting-diversity-test-v1.json'),
                                  ('regression',a.regression_root,a.regression_cpu,'evidence/lighting-diversity-regression-v1.json')]:
        raw,cpu=Path(raw).resolve(),Path(cpu).resolve();source=read(raw/'run.json');evaluated=read(ROOT/evidence)
        if source['status']!='succeeded' or evaluated['status']!='succeeded' or evaluated['evaluation_scope']!=split:
            raise ValueError('Original rendered/evaluated batch incomplete')
        if evaluated['renderer_run_sha256']!=digest(raw/'run.json') or evaluated['model_lock_sha256']!=binding['model_lock_sha256']:
            raise ValueError('Original render/model provenance differs')
        provenance[split]={'render_report_sha256':digest(raw/'run.json'),'cpu_evidence':evidence,'cpu_evidence_sha256':digest(ROOT/evidence)}
        if split=='test':
            if source['phase']!='test' or source['plan_sha256']!=digest(ROOT/'scenes/lighting-diversity-v1.json'):raise ValueError('Test plan differs')
            definition=next(s for s in source['plan']['scenes'] if s['split']=='test')
            seq=definition['id'];frames=source['cases'];scene=source['scenes'][seq]
            temporal.validate_sequence({'id':seq,'frames':frames},{'id':seq},{**source['plan']['test_sequence'],'camera_target':source['plan']['camera_target']})
            sequences.append((split,seq,frames,scene,source,raw,cpu,evaluated))
        else:
            if source['plan_sha256']!=digest(ROOT/'scenes/lighting-motion-v1.json'):raise ValueError('Regression plan differs')
            if len(source['sequences'])!=2:raise ValueError('Missing regression sequence')
            for scene,definition in zip(source['sequences'],source['plan']['sequences']):
                temporal.validate_sequence(scene,definition,source['plan'])
                sequences.append((split,scene['id'],scene['frames'],scene,source,raw,cpu,evaluated))
    if sum(len(s[2]) for s in sequences)!=112:raise ValueError('Expected all 48 test and 64 regression frames')
    report={'schema_version':1,'status':'running',**binding,'source_provenance':provenance,'sequences':[], 'cases':[],
            'candidate':'scene','training_performed':False,'selection_performed':False,'driver_sha256':digest(__file__),
            'shared_gpu_runner_sha256':digest(ROOT/'scripts/lighting_gpu_run.py'),'gpu_contract_sha256':digest(ROOT/'enr/lighting_gpu.py'),
            'fidelity_gates_code_sha256':digest(ROOT/'scripts/summarize_lighting_diversity.py'),
            'feature_loader_sha256':digest(ROOT/'scripts/lighting_diversity_data.py'),
            'regression_loader_sha256':digest(ROOT/'scripts/evaluate_lighting_motion.py'),
            'numpy':np.__version__,'scope':'GPU numerical parity and the unchanged synthetic linear-space fidelity gates; no Enfusion scene inputs or performance',
            'packed_input_retention':'Temporary packed tensors removed after native parity and file/memory hash checks. Reconstruct from retained original EXR/config records using the recorded loaders. All native outputs retained.'}
    def save():write(out/'run.json',report)
    save()
    try:
        for split,seq,frames,scene,source,raw,cpu,evaluated in sequences:
            cpu_cases={c['index']:c for c in evaluated['cases'] if c['sequence']==seq}
            if sorted(cpu_cases)!=list(range(len(frames))):raise ValueError('Missing or duplicate retained CPU frames')
            previous=None;revised=[]
            for frame in frames:
                index=frame['index'];original=cpu_cases[index];identity=original['id'];print('Starting '+identity,flush=True)
                if split=='test':
                    d=load_case(raw,source,frame);d['paired']=d['target'];d['target']=d['independent']
                else:d=load_frame(raw/seq/f'{index:04d}',frame,scene,source['plan'])
                old_path=cpu/identity/'scene.npy'
                if digest(old_path)!=original['outputs']['scene']['linear_rgba_sha256']:raise ValueError('Retained CPU output changed')
                retained=np.load(old_path,allow_pickle=False)
                records=lighting_gpu.pack(d['x'],d['rgb'],d['alpha'],d['valid'])
                folder=out/identity
                native=run(folder,a.exe,records,model,binding['models']['scene'],gpu_plan['limits'],save_linear=False)
                actual=np.fromfile(folder/'output.fp32',dtype='<f4').reshape(*records.shape[:2],7)[...,3:7];value=actual[...,:3]
                delta=np.abs(actual[...,:3].astype(np.float64)-retained[...,:3])
                tolerance=gpu_plan['limits']['linear_rgb_absolute_tolerance']+gpu_plan['limits']['linear_rgb_relative_tolerance']*np.abs(retained[...,:3])
                old_parity={'linear_rgb_within_tolerance':bool(np.all(delta<=tolerance)),
                            'alpha_bits_exact':bool(np.array_equal(actual[...,3].view(np.uint32),retained[...,3].view(np.uint32))),
                            'maximum_absolute_linear_rgb_error':float(delta.max()),'maximum_error_fraction_of_tolerance':float((delta/tolerance).max())}
                if not old_parity['linear_rgb_within_tolerance'] or not old_parity['alpha_bits_exact']:raise ValueError('GPU differs from retained CPU evaluation')
                case=copy.deepcopy(original);ids=d['ids'];objects=scene['objects']
                masks={'all':None,'object_edges':(ids>0)&~temporal.interior(ids),
                       'thin_posts':np.isin(ids,[o['id'] for n,o in objects.items() if n.startswith('post-')]),
                       'markings':np.isin(ids,[o['id'] for n,o in objects.items() if n.startswith('mark-')])}
                case['metrics']['scene']={region:metric(value,d['target'],mask) if mask is None or mask.any() else None for region,mask in masks.items()}
                case['paired_reference_metrics']['scene']=metric(value,d['paired'])
                case['marking_contrast']['scene']=marking_contrast(value,ids,objects)
                # Display-referred metrics have not been recomputed for native outputs.
                case['outputs']['scene']={'native_output_sha256':digest(folder/'output.fp32'),'linear_rgba_columns':[3,7],'display_evaluated':False}
                error=np.log1p(value)-np.log1p(d['target']);paired_error=np.log1p(value)-np.log1p(d['paired'])
                if previous is not None:
                    xy,mask,coverage=temporal.correspondence(d,previous,previous['camera_matrix'],evaluated['plan']['vertical_fov_degrees'])
                    if coverage!=original['temporal']['coverage']:raise ValueError('Temporal correspondence coverage changed')
                    case['temporal']['error_change']['scene']=temporal.error_change(error,previous['error'],xy,mask)
                    case['temporal']['paired_error_change']['scene']=temporal.error_change(paired_error,previous['paired_error'],xy,mask)
                    unmatched=temporal.interior(ids)&~mask
                    case['unmatched_interior_metrics']['scene']=metric(value,d['target'],unmatched) if unmatched.any() else None
                previous={k:d[k] for k in ('position','normal','ids')};previous.update(camera_matrix=frame['camera_matrix'],error=error,paired_error=paired_error)
                case['gpu_run']={'report_sha256':digest(folder/'run.json'),**native};case['retained_cpu_parity']=old_parity
                # Original source passes are retained. This packed file is a reconstructible transfer buffer.
                input_path=folder/'input.fp32'
                if input_path.resolve().parent!=folder or input_path.is_symlink() or digest(input_path)!=hashlib.sha256(memoryview(records)).hexdigest():
                    raise ValueError('Transient input changed or escaped')
                case['packed_input_recipe']={'source_split':split,'sequence':seq,'index':index,'sha256':native['input_sha256'],
                                              'source_report_sha256':provenance[split]['render_report_sha256'],'removed':False}
                report['cases'].append(case);revised.append(case);save()
                input_path.unlink();case['packed_input_recipe']['removed']=True;save()
                print(json.dumps({'id':identity,'passed':native['comparison']['passed'],'retained_cpu':old_parity}),flush=True)
            summary={'id':seq,'split':split,'frames':len(frames),**summarize(revised,'scene',evaluated['plan']['gates'],include_display=False)}
            report['sequences'].append(summary);save()
        report['status']='succeeded'
    except Exception as error:report.update(status='failed',error=str(error));raise
    finally:save()
    print(json.dumps({'status':report['status'],'sequences':report['sequences']}))


if __name__=='__main__':main()
