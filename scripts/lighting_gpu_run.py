"""Shared offline lighting GPU invocation with an independent CPU check."""
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr import lighting,lighting_gpu,diversity
from enr.references import digest


def write(path,value):path.write_bytes((json.dumps(value,indent=2,allow_nan=False)+'\n').encode('utf-8'))


def locked_models():
    plan_path=ROOT/'scenes/lighting-gpu-v1.json'
    plan=json.loads(plan_path.read_text(encoding='utf-8'))
    lock_path=ROOT/plan['model_lock'];lock=json.loads(lock_path.read_text(encoding='utf-8'))
    models={};records={}
    if not lock['training_complete'] or lock['test_accessed'] or lock['selected_candidate']!='scene':
        raise ValueError('Unexpected model selection lock')
    for variant in plan['variants']:
        entry=lock['models'][variant];path=lock_path.parent/entry['file']
        if digest(path)!=entry['sha256']:raise ValueError('Frozen model changed')
        model,record=lighting.load(path)
        if record['features']!=diversity.names(variant):raise ValueError('Model feature order differs')
        models[variant]=model;records[variant]={'file':path.relative_to(ROOT).as_posix(),'sha256':digest(path),'features':record['features']}
    return models,{'plan':plan,'plan_sha256':digest(plan_path),'model_lock_sha256':digest(lock_path),'models':records}


def run(out,exe,records,model,identity,limits,warmup=0,samples=1,allow_no_gpu=False,save_linear=True):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    exe=Path(exe).resolve();h,w,fields=records.shape;columns=fields-5
    lighting_gpu.dimensions(w,h)
    if columns!=len(model['mean']) or not records.flags.c_contiguous or records.dtype!=np.dtype('<f4'):
        raise ValueError('Invalid packed lighting records')
    records.tofile(out/'input.fp32')
    shader=out/'model.hlsl';shader.write_bytes(lighting_gpu.hlsl(model).encode('utf-8'))
    report={'schema_version':1,'status':'running','model':identity,'dimensions':[w,h],
            'input_sha256':digest(out/'input.fp32'),'input_bytes':records.nbytes,'shader_sha256':digest(shader),
            'native_executable_sha256':digest(exe),'limits':limits,'warmup':warmup,'samples':samples,
            'scope':'Standalone FP32 lighting inference; features are prepared on CPU; no capture, presentation or complete-frame timing'}
    started=time.perf_counter();write(out/'run.json',report)
    try:
        command=[str(exe),str((out/'input.fp32').resolve()),str((out/'output.fp32').resolve()),str((out/'gpu.json').resolve()),
                 str(w),str(h),str(shader.resolve()),str(warmup),str(samples),'lighting'+str(columns)]
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=180)
        (out/'console.log').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
        report['process_exit_code']=result.returncode
        report['native_process_all_dispatches_ms']=1000*(time.perf_counter()-started)
        if result.returncode:
            if allow_no_gpu and 'No hardware D3D12 FL12_0 adapter' in result.stderr:
                report.update(status='skipped',reason='No hardware D3D12 adapter; no GPU correctness or performance claim')
                return report
            raise ValueError('Native lighting process failed: '+result.stderr.strip())
        gpu=json.loads((out/'gpu.json').read_text(encoding='utf-8'))
        if (gpu['record_mode']!='lighting'+str(columns) or gpu['pixels']!=w*h or gpu['input_bytes']!=records.nbytes
                or gpu['output_bytes']!=w*h*7*4 or gpu['input_stride_bytes']!=fields*4 or gpu['output_stride_bytes']!=28
                or gpu['warmup_dispatches']!=warmup or gpu['measured_dispatches']!=samples or len(gpu['dispatch_ms'])!=samples):
            raise ValueError('Native buffer/timing contract differs')
        if not np.isfinite(gpu['dispatch_ms']).all() or min(gpu['dispatch_ms'])<0:raise ValueError('Invalid native timing')
        actual=np.fromfile(out/'output.fp32',dtype='<f4').reshape(h,w,7)
        reference_started=time.perf_counter();expected=lighting_gpu.reference(records,model)
        report['cpu_reference_ms']=1000*(time.perf_counter()-reference_started)
        report['comparison']=lighting_gpu.compare(actual,expected,records,limits)
        report['gpu']=gpu;report['output_sha256']=digest(out/'output.fp32');report['gpu_report_sha256']=digest(out/'gpu.json')
        # Reconstructed linear RGBA is the artifact consumed by fidelity evaluation.
        if save_linear:
            np.save(out/'linear.npy',actual[...,3:7])
            report['linear_rgba_sha256']=digest(out/'linear.npy')
        report['linear_rgba_storage']='linear.npy and output.fp32 columns 3:7' if save_linear else 'output.fp32 columns 3:7; no redundant NPY copy'
        report['status']='succeeded' if report['comparison']['passed'] else 'failed'
        if not report['comparison']['passed']:raise ValueError('Native lighting failed the predeclared CPU tolerances')
        return report
    except Exception as error:
        report.update(status='failed',error=str(error));raise
    finally:
        report['total_ms']=1000*(time.perf_counter()-started);write(out/'run.json',report)


if __name__=='__main__':raise SystemExit('Use scripts/gpu_lighting_smoke.py or scripts/evaluate_lighting_gpu.py')
