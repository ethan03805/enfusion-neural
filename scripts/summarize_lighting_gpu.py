"""Bind native lighting outputs, frozen models, complete frame checks and failures."""
import argparse
import json
from pathlib import Path
import re

import numpy as np

from lighting_gpu_run import ROOT,locked_models,write
from enr import lighting_gpu
from enr.references import digest


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def checked_trial(root,name,record,expected_status='succeeded'):
    if not re.fullmatch(r'[a-z0-9-]+',name):raise ValueError('Invalid trial name')
    folder=(root/name).resolve()
    if folder.parent!=root.resolve() or folder.is_symlink():raise ValueError('Trial path escaped')
    actual=read(folder/'run.json')
    if digest(folder/'run.json')!=record['report_sha256'] or any(record.get(k)!=v for k,v in actual.items()):
        raise ValueError('Native trial report changed')
    if actual['status']!=expected_status or actual['process_exit_code']!=0:raise ValueError('Native process did not complete as recorded')
    if digest(folder/'model.hlsl')!=actual['shader_sha256'] or digest(folder/'output.fp32')!=actual['output_sha256']:
        raise ValueError('Native shader/output changed')
    if digest(folder/'gpu.json')!=actual['gpu_report_sha256'] or read(folder/'gpu.json')!=actual['gpu']:
        raise ValueError('Native timings changed')
    w,h=actual['dimensions'];raw=folder/'output.fp32'
    if raw.stat().st_size!=w*h*28:raise ValueError('Native output dimensions differ')
    data=np.memmap(raw,dtype='<f4',mode='r',shape=(h,w,7))
    finite=bool(np.isfinite(data).all());bound=float(np.max(np.abs(data[...,:3])))
    if not finite or (expected_status=='succeeded' and (bound>.25 or not actual['comparison']['passed'])):
        raise ValueError('Native output validity differs')
    return {'id':name,'report_sha256':digest(folder/'run.json'),'dimensions':[w,h],
            'model':actual['model'],'shader_sha256':actual['shader_sha256'],'input_sha256':actual['input_sha256'],
            'output_sha256':actual['output_sha256'],'output_bytes':raw.stat().st_size,'native_executable_sha256':actual['native_executable_sha256'],
            'maximum_absolute_residual':bound,'comparison':actual['comparison'],'gpu':actual['gpu'],
            'native_process_all_dispatches_ms':actual['native_process_all_dispatches_ms'],
            'cpu_reference_ms':actual['cpu_reference_ms']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('smoke','initial','remainder','frames','out'):p.add_argument('--'+name,required=True)
    a=p.parse_args();out=Path(a.out)
    if out.exists():raise ValueError('Portable output exists')
    models,binding=locked_models();smoke_root=Path(a.smoke);smoke=read(smoke_root/'run.json')
    if smoke['status']!='succeeded' or any(smoke[k]!=v for k,v in binding.items()):raise ValueError('Smoke experiment incomplete or model/plan changed')
    expected=[f'{v}-{w}x{h}' for w,h in binding['plan']['smoke_dimensions'] for v in binding['plan']['variants']]+['scene-1440p-benchmark']
    if [r['id'] for r in smoke['runs']]!=expected:raise ValueError('Missing/repeated numerical controls')
    controls=[];retention=[]
    for r in smoke['runs']:
        controls.append(checked_trial(smoke_root,r['id'],r))
        path=smoke_root/('fixture-retention-'+r['id'])/'run.json';kept=read(path)
        if len(kept['files'])!=1 or not kept['files'][0]['byte_exact_regeneration'] or not kept['files'][0]['removed']:
            raise ValueError('Missing exact fixture regeneration evidence')
        if kept['files'][0]['sha256']!=r['input_sha256']:raise ValueError('Retention hash differs')
        for name,sha in kept['snapshots'].items():
            if digest(path.parent/name)!=sha:raise ValueError('Fixture recipe snapshot changed')
        retention.append({'trial':r['id'],'report_sha256':digest(path),'recipe':kept})
    initial_root=Path(a.initial);initial=read(initial_root/'run.json')
    remainder_root=Path(a.remainder);remainder=read(remainder_root/'run.json')
    if initial['status']!='failed' or initial['error']!='182476800 requested and 0 written' or len(initial['runs'])!=19:
        raise ValueError('Initial disk failure differs')
    old_controls=[checked_trial(initial_root,r['id'],r) for r in initial['runs']]
    if remainder['status']!='failed' or len(remainder['runs'])!=1:raise ValueError('Remainder outcome differs')
    old_controls.append(checked_trial(remainder_root,remainder['runs'][0]['id'],remainder['runs'][0]))
    failed_path=remainder_root/'rgb-3840x2160/run.json';failed=read(failed_path)
    failed_control=checked_trial(remainder_root,'rgb-3840x2160',{'report_sha256':digest(failed_path),**failed},'failed')
    if failed['comparison']['checks']['bounded_residual'] or not all(v for k,v in failed['comparison']['checks'].items() if k!='bounded_residual'):
        raise ValueError('Expected strict-bound-only failure')
    failed_pixels=np.memmap(failed_path.parent/'output.fp32',dtype='<f4',mode='r',shape=(2160,3840,7))
    bad=np.argwhere(np.abs(failed_pixels[...,:3])>.25)
    failed_control['bound_violations']=[{'y':int(y),'x':int(x),'channel':int(c),'value':float(failed_pixels[y,x,c])} for y,x,c in bad]
    frames_root=Path(a.frames);frames=read(frames_root/'run.json')
    if frames['status']!='succeeded' or len(frames['cases'])!=112 or len(frames['sequences'])!=3:
        raise ValueError('All 112 frames must complete')
    if frames['training_performed'] or frames['selection_performed'] or any(frames[k]!=v for k,v in binding.items()):
        raise ValueError('Frozen frame experiment changed')
    for key,path in [('driver_sha256','scripts/evaluate_lighting_gpu.py'),('shared_gpu_runner_sha256','scripts/lighting_gpu_run.py'),
                     ('fidelity_gates_code_sha256','scripts/summarize_lighting_diversity.py'),
                     ('feature_loader_sha256','scripts/lighting_diversity_data.py'),('regression_loader_sha256','scripts/evaluate_lighting_motion.py')]:
        if frames[key]!=digest(ROOT/path):raise ValueError('Executed frame code changed: '+path)
    if frames['gpu_contract_sha256']!=digest(frames_root/'executed-lighting_gpu.py') or smoke['gpu_contract_sha256']!=digest(smoke_root/'executed-lighting_gpu.py'):
        raise ValueError('Executed GPU contract snapshot differs')
    for source in frames['source_provenance'].values():
        if digest(ROOT/source['cpu_evidence'])!=source['cpu_evidence_sha256']:raise ValueError('Retained CPU evidence changed')
    frame_records=[]
    for case in frames['cases']:
        native=checked_trial(frames_root,case['id'],case['gpu_run'])
        if not case['retained_cpu_parity']['linear_rgb_within_tolerance'] or not case['retained_cpu_parity']['alpha_bits_exact']:
            raise ValueError('Retained CPU parity failed')
        if not case['packed_input_recipe']['removed'] or case['packed_input_recipe']['sha256']!=native['input_sha256']:
            raise ValueError('Source reconstruction recipe differs')
        frame_records.append({k:case[k] for k in ['id','sequence','split','index','metrics','paired_reference_metrics','marking_contrast',
                                                 'retained_cpu_parity','packed_input_recipe']})
        frame_records[-1]['native']=native
        if 'temporal' in case:frame_records[-1]['temporal']=case['temporal']
    for sequence in frames['sequences']:
        indices=[c['index'] for c in frame_records if c['sequence']==sequence['id']]
        if indices!=list(range(sequence['frames'])):raise ValueError('Incomplete sequence frame order')
    import hashlib
    shader_hashes={binding['models'][variant]['sha256']:hashlib.sha256(lighting_gpu.hlsl(model).encode('utf-8')).hexdigest() for variant,model in models.items()}
    for native in controls+[v['native'] for v in frame_records]:
        if native['shader_sha256']!=shader_hashes[native['model']['sha256']]:raise ValueError('Current model shader differs from executed shader')
    result={'schema_version':1,'operation':'native-lighting-graph','status':'succeeded',**binding,
            'bound_followup':read(ROOT/'scenes/lighting-gpu-bound-followup-v2.json'),
            'bound_followup_sha256':digest(ROOT/'scenes/lighting-gpu-bound-followup-v2.json'),
            'summarizer_sha256':digest(__file__),'smoke_report_sha256':digest(smoke_root/'run.json'),
            'executed_gpu_contract_sha256':frames['gpu_contract_sha256'],'current_gpu_contract_sha256':digest(ROOT/'enr/lighting_gpu.py'),
            'current_shader_bytes_match_all_final_runs':True,
            'numerical_controls':controls,'fixture_retention':retention,
            'initial_failures':{'disk_write':{'report_sha256':digest(initial_root/'run.json'),'error':initial['error'],'successful_controls_before_failure':19},
                                'prior_successful_controls':old_controls,'rgb_4k_bound':failed_control},
            'frame_report_sha256':digest(frames_root/'run.json'),'source_provenance':frames['source_provenance'],
            'sequences':frames['sequences'],'frames':frame_records,
            'verified':{'all_21_numerical_controls':True,'all_112_frames_match_cpu_tolerances':True,'alpha_and_invalid_fallback_exact':True,
                        'synthetic_test_fidelity_gates':next(s['passed'] for s in frames['sequences'] if s['split']=='test'),
                        'enfusion_scene_inputs':False,'enfusion_neural_execution':False,'actual_arma_model_fidelity':False,'complete_frame_performance':False},
            'limits':['Standalone FP32 execution on prepared CPU features; compilation, transfers and file I/O are separate from dispatch.',
                      'All original test/regression frames reused; no rendering, training or candidate selection.',
                      'Source/affine/RGB/old-model metrics remain the hash-bound CPU controls. Only scene-model metrics recomputed from GPU output.',
                      'No new display-referred image metrics; all fidelity gates here use the original linear/log-space definition.',
                      'Complete native output records retained. Generated numerical inputs and derived transfer buffers are reconstructible as recorded.']}
    write(out,result)
    print(json.dumps({'verified':result['verified'],'sequences':[{k:s[k] for k in ['id','passed','gates']} for s in result['sequences']],
                      'benchmark':controls[-1]['gpu']}))


if __name__=='__main__':main()
