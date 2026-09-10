"""Bounded unchanged-author IAT exposure evaluation on CPU and RX 7800 XT."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

import cv2
import numpy as np
import onnx
import onnxruntime as ort
from PIL import Image
import timm
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json


def stats(values):
    return {'count': len(values), 'median': float(np.median(values)), 'p95': float(np.percentile(values,95)),
            'p99': float(np.percentile(values,99)), 'max': float(np.max(values)), 'min': float(np.min(values))}


def png(rgb, path):
    Image.fromarray(np.rint(np.clip(rgb,0,1)*255).astype(np.uint8)).save(path)


def smooth(a, b, x):
    t = np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)


def protect(source, low_input, low_output):
    height, width, _ = source.shape
    residual = cv2.resize(low_output-low_input, (width,height), interpolation=cv2.INTER_LINEAR)
    finite = np.isfinite(residual).all(axis=2)
    residual = np.nan_to_num(residual, nan=0, posinf=0, neginf=0)
    luminance = source @ np.array([.2126,.7152,.0722],dtype=np.float32)
    weight = smooth(.02,.08,luminance)*(1-smooth(.85,.98,luminance))
    yy,xx = np.mgrid[:height,:width]
    excluded = (yy<height*.08)|(yy>=height*.92)|((np.abs(xx-width*.5)<width*.025)&(np.abs(yy-height*.5)<height*.025))
    weight[excluded|~finite] = 0
    before_clip = source+.5*weight[:,:,None]*np.clip(residual,-.08,.08)
    return before_clip, np.clip(before_clip,0,1), int((~finite).sum())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    a = p.parse_args(); out = a.out.resolve(); out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(__file__,out/'driver.py')
    plan_path = ROOT/'scenes/playable-iat-evaluation-v1.json'
    plan = json.loads(plan_path.read_text())
    source = ROOT/'runs/pretrained/iat-exposure-v1'
    provenance = json.loads((source/'source.json').read_text())
    report = {'schema_version':1,'status':'started','started_at':datetime.now(timezone.utc).isoformat(),
        'plan_sha256':digest(plan_path),'driver_sha256':digest(Path(__file__)),
        'provenance_sha256':digest(source/'source.json'),'images':[]}
    write_json(out/'report.json',report)
    session = None
    try:
        for name,row in provenance['files'].items():
            if digest(source/name)!=row['sha256']:
                raise ValueError('Changed author artifact: '+name)
        if provenance['revision']!=plan['revision'] or digest(source/plan['checkpoint'])!=plan['checkpoint_sha256']:
            raise ValueError('Changed pinned checkpoint/source')
        active = subprocess.check_output(['powershell','-NoProfile','-Command',
            'Get-Process -Name ArmaReforgerSteam,ArmaReforgerWorkbenchSteamDiag,enr_companion -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName; exit 0'],text=True).strip()
        if active: raise ValueError('GPU experiment sessions active: '+active)
        adapters = [json.loads(line) for line in subprocess.check_output([str(ROOT/'build/Release/enr_adapter_info.exe')],text=True).splitlines()]
        adapter = adapters[0]
        if adapter['description']!='AMD Radeon RX 7800 XT' or adapter['software']:
            raise ValueError('Unexpected DirectML adapter 0')
        report.update(adapter=adapter,precision='FP32',runtime=ort.__version__,torch=torch.__version__,timm=timm.__version__,
            input_shape=plan['input_shape'],scope='Game stopped. Synchronized ONNX Runtime calls include upload and readback of all three author outputs: mul, add and enhanced. Decode, resize, source protection, file encoding and initialization excluded; not pure GPU time or complete application performance.')
        sys.path.insert(0,str(source/'IAT_enhance'))
        from model.IAT_main import IAT
        torch.set_num_threads(8); cv2.setNumThreads(8); torch.manual_seed(0)
        model = IAT(type='exp').eval()
        model.load_state_dict(torch.load(source/plan['checkpoint'],map_location='cpu',weights_only=True),strict=True)
        report['parameters'] = sum(p.numel() for p in model.parameters())
        width,height = plan['input_shape'][3],plan['input_shape'][2]
        for index,item in enumerate(plan['inputs']):
            path = ROOT/item['path']
            if digest(path)!=item['sha256']: raise ValueError('Changed planned image')
            full_image = Image.open(path).convert('RGB')
            if full_image.size!=(2560,1440): raise ValueError('Unexpected native source dimensions')
            full = np.asarray(full_image,dtype=np.float32)/255
            small_image = full_image.resize((width,height),Image.Resampling.BILINEAR)
            small = np.asarray(small_image,dtype=np.float32)/255
            x = np.ascontiguousarray(small.transpose(2,0,1)[None])
            np.save(out/f'{index:02d}-input.npy',x)
            small_image.save(out/f'{index:02d}-source.png')
            with torch.inference_mode():
                started = time.perf_counter(); references = [t.numpy() for t in model(torch.from_numpy(x))]
                cpu_ms = (time.perf_counter()-started)*1000
            for name,value in zip(('mul','add','enhanced'),references):
                np.save(out/f'{index:02d}-cpu-{name}.npy',value)
            if index==0:
                graph = out/'model.onnx'
                torch.onnx.export(model,torch.from_numpy(x),str(graph),opset_version=17,input_names=['rgb'],
                    output_names=['mul','add','enhanced'],do_constant_folding=True,dynamo=False)
                onnx.checker.check_model(onnx.load(graph)); report['onnx_sha256']=digest(graph)
                options = ort.SessionOptions(); options.enable_mem_pattern=False
                options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
                options.add_session_config_entry('session.disable_cpu_ep_fallback','1')
                options.enable_profiling=True; options.profile_file_prefix=str(out/'profile')
                session = ort.InferenceSession(str(graph),sess_options=options,providers=[('DmlExecutionProvider',{'device_id':0})])
                session.disable_fallback(); report['providers']=session.get_providers()
            warmups,samples = (5,20) if index==0 else (1,5)
            for _ in range(warmups): session.run(None,{'rgb':x})
            timings=[]
            for _ in range(samples):
                started=time.perf_counter(); outputs=session.run(None,{'rgb':x})
                timings.append((time.perf_counter()-started)*1000)
            parity = {}
            for name,cpu,gpu in zip(('mul','add','enhanced'),references,outputs):
                if not np.isfinite(gpu).all(): raise ValueError('Nonfinite author output')
                np.save(out/f'{index:02d}-dml-{name}.npy',gpu)
                error=np.abs(cpu-gpu)
                parity[name]={'max_abs':float(error.max()),'mean_abs':float(error.mean()),
                    'passed':bool(error.max()<=plan['parity']['max_abs'] and error.mean()<=plan['parity']['mean_abs'])}
            if not all(v['passed'] for v in parity.values()): raise ValueError('CPU/DirectML parity failed')
            raw=outputs[2][0].transpose(1,2,0)
            png(raw,out/f'{index:02d}-raw.png')
            png(cv2.resize(raw,(2560,1440),interpolation=cv2.INTER_LINEAR),out/f'{index:02d}-raw-full.png')
            preclip,protected,fallback = protect(full,small,raw)
            np.save(out/f'{index:02d}-protected-preclip.npy',preclip)
            png(protected,out/f'{index:02d}-protected.png')
            source_codes=np.rint(small*255)
            raw_codes=np.rint(np.clip(raw,0,1)*255)
            protected_codes=np.rint(protected*255)
            full_codes=np.rint(full*255)
            clipped=lambda after,before:float(np.mean(((after<=0)&(before>0))|((after>=255)&(before<255))))
            row={**item,'cpu_reference_ms':cpu_ms,'warmups':warmups,'timings_ms':timings,'timing':stats(timings),'parity':parity,
                'raw_range':[float(raw.min()),float(raw.max())],
                'raw_black_channel_fraction':float(np.mean(raw_codes<=0)),'raw_white_channel_fraction':float(np.mean(raw_codes>=255)),
                'raw_newly_clipped_channel_fraction':clipped(raw_codes,source_codes),
                'raw_rgb_mae_codes':float(np.mean(np.abs(raw_codes-source_codes))),
                'protected_preclip_range':[float(preclip.min()),float(preclip.max())],
                'protected_rgb_mae_codes':float(np.mean(np.abs(protected_codes-full_codes))),
                'protected_max_change_codes':float(np.max(np.abs(protected_codes-full_codes))),
                'protected_newly_clipped_channel_fraction':clipped(protected_codes,full_codes),
                'protected_fallback_pixels':fallback,
                'artifact_hashes':{p.name:digest(p) for p in out.glob(f'{index:02d}-*') if p.is_file()}}
            report['images'].append(row); write_json(out/'report.json',report)
            print(json.dumps({k:v for k,v in row.items() if k!='artifact_hashes'}),flush=True)
        report['provisional_cost_pass']=all(r['timing']['p95']<=plan['provisional_p95_call_limit_ms'] for r in report['images'])
        report['status']='completed'
    except Exception as error:
        report.update(status='failed',error=repr(error),traceback=traceback.format_exc())
        raise
    finally:
        if session is not None:
            profile=Path(session.end_profiling())
            report.update(profile_file=profile.name,profile_sha256=digest(profile))
            events=json.loads(profile.read_text())
            report['profile_provider_events']=dict(Counter(e.get('args',{}).get('provider') for e in events if e.get('args',{}).get('provider')))
            if set(report['profile_provider_events'])!={'DmlExecutionProvider'}:
                report['status']='failed'; report['provider_error']='Unexpected non-DirectML execution events'
        report['finished_at']=datetime.now(timezone.utc).isoformat()
        write_json(out/'report.json',report)
        print(json.dumps({k:v for k,v in report.items() if k not in ('images','traceback')},indent=2))


if __name__=='__main__': main()
