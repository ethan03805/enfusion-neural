"""Bounded pinned Depth Anything V2 Small CPU/DirectML comparison; no lighting effect."""
import argparse
from collections import Counter
import importlib.metadata
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
import torch
import torch.nn.functional as F

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr.references import digest,write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--short-side',type=int,choices=[252,392],required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();out=a.out.resolve()
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True);shutil.copyfile(__file__,out/'driver.py')
    plan_path=ROOT/'scenes/playable-depth-evaluation-v1.json';plan=json.loads(plan_path.read_text())
    report={'schema_version':1,'status':'started','plan_sha256':digest(plan_path),'driver_sha256':digest(Path(__file__)),
        'short_side':a.short_side,'precision':'FP32','images':[]}
    write_json(out/'report.json',report)
    try:
        active=subprocess.check_output(['powershell','-NoProfile','-Command',"Get-Process -Name ArmaReforgerSteam,ArmaReforgerWorkbenchSteamDiag,enr_companion -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName; exit 0"],text=True).strip()
        if active:raise ValueError('Stop owned game/GPU sessions before evaluation: '+active)
        source=ROOT/'runs/pretrained/depth-anything-v2-source-v1'
        provenance_path=ROOT/'runs/pretrained/depth-anything-v2-small-v1/source.json';provenance=json.loads(provenance_path.read_text())
        for path,sha in provenance['source_hashes'].items():
            if digest(ROOT/path)!=sha:raise ValueError('Author source changed: '+path)
        checkpoint=provenance_path.parent/'depth_anything_v2_vits.pth'
        if digest(checkpoint)!=plan['checkpoint_sha256']:raise ValueError('Checkpoint differs')
        report['provenance_sha256']=digest(provenance_path)
        report['adapter_info']=subprocess.check_output([str(ROOT/'build/Release/enr_adapter_info.exe')],text=True)
        if '7800 XT' not in report['adapter_info']:raise ValueError('Expected RX 7800 XT adapter inventory')
        report['software']={name:importlib.metadata.version(name) for name in ['torch','torchvision','opencv-python-headless','numpy','onnx','onnxruntime-directml']}
        torch.set_num_threads(8);torch.manual_seed(0)
        sys.path.insert(0,str(source));from depth_anything_v2.dpt import DepthAnythingV2
        model=DepthAnythingV2(encoder='vits',features=64,out_channels=[48,96,192,384]).eval()
        model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True),strict=True)
        report['parameters']=sum(t.numel() for t in model.parameters())
        tensors=[];references=[]
        for i,row in enumerate(plan['images']):
            path=ROOT/row['path']
            if digest(path)!=row['sha256']:raise ValueError('Source RGB changed')
            raw=cv2.imread(str(path));tensor,original=model.image2tensor(raw,a.short_side)
            tensor=tensor.cpu().contiguous()
            start=time.perf_counter()
            with torch.inference_mode():ref=model(tensor).numpy()
            elapsed=(time.perf_counter()-start)*1000
            if not np.isfinite(ref).all():raise ValueError('Nonfinite CPU output')
            np.save(out/f'{i:02d}-input.npy',tensor.numpy());np.save(out/f'{i:02d}-cpu.npy',ref)
            tensors.append(tensor);references.append(ref)
            report['images'].append({'name':row['name'],'source':row['path'],'source_sha256':row['sha256'],
                'tensor_shape':list(tensor.shape),'source_height_width':list(original),'cpu_ms':elapsed,
                'input_sha256':digest(out/f'{i:02d}-input.npy'),'cpu_sha256':digest(out/f'{i:02d}-cpu.npy')})
        if tensors[0].shape!=tensors[1].shape:raise ValueError('Expected same static tensor shape')
        graph=out/'model.onnx'
        torch.onnx.export(model,tensors[0],str(graph),opset_version=17,input_names=['rgb'],output_names=['relative_depth'],do_constant_folding=True,dynamo=False)
        onnx.checker.check_model(onnx.load(graph));report['onnx_sha256']=digest(graph)
        options=ort.SessionOptions();options.enable_mem_pattern=False;options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
        options.add_session_config_entry('session.disable_cpu_ep_fallback','1')
        options.enable_profiling=True;options.profile_file_prefix=str(out/'profile')
        session=ort.InferenceSession(str(graph),sess_options=options,providers=[('DmlExecutionProvider',{'device_id':0})])
        report['providers']=session.get_providers()
        for i,(tensor,ref) in enumerate(zip(tensors,references)):
            feed={'rgb':tensor.numpy()}
            for _ in range(5 if i==0 else 1):session.run(None,feed)
            timings=[]
            for _ in range(20 if i==0 else 5):
                start=time.perf_counter();prediction=session.run(None,feed)[0];timings.append((time.perf_counter()-start)*1000)
            if not np.isfinite(prediction).all():raise ValueError('Nonfinite DirectML output')
            np.save(out/f'{i:02d}-dml.npy',prediction)
            scale=max(float(np.ptp(ref)),1e-6);error=np.abs(prediction-ref)
            row=report['images'][i]
            row.update({'milliseconds':timings,'median_ms':float(np.median(timings)),'p95_ms':float(np.percentile(timings,95)),
                'dml_sha256':digest(out/f'{i:02d}-dml.npy'),'range':[float(prediction.min()),float(prediction.max())],
                'parity':{'raw_max':float(error.max()),'raw_mean':float(error.mean()),'cpu_range':scale,
                    'normalized_max':float(error.max())/scale,'normalized_mean':float(error.mean())/scale,
                    'passed':bool(error.max()/scale<=.001 and error.mean()/scale<=.0001)}})
            with torch.inference_mode():full=F.interpolate(torch.from_numpy(prediction)[:,None],tuple(row['source_height_width']),mode='bilinear',align_corners=True)[0,0].numpy()
            np.save(out/f'{i:02d}-full-depth.npy',full)
            visual=np.rint((full-full.min())/max(float(np.ptp(full)),1e-6)*255).astype(np.uint8)
            Image.fromarray(visual).save(out/f'{i:02d}-relative-depth.png')
            row['full_depth_sha256']=digest(out/f'{i:02d}-full-depth.npy')
            row['visual_sha256']=digest(out/f'{i:02d}-relative-depth.png')
        profile=Path(session.end_profiling());events=json.loads(profile.read_text())
        report['profile_file']=profile.name;report['profile_sha256']=digest(profile)
        report['profile_provider_events']=dict(Counter(e.get('args',{}).get('provider') for e in events if e.get('args',{}).get('provider')))
        if set(report['profile_provider_events'])!={'DmlExecutionProvider'}:raise ValueError('Unexpected provider execution')
        report['parity_pass']=all(r['parity']['passed'] for r in report['images'])
        report['provisional_cost_pass']=all(r['p95_ms']<=plan['provisional_p95_call_limit_ms'] for r in report['images'])
        report['scope']='Game stopped; synchronized DirectML calls including upload/readback only. CPU preprocessing/full-size interpolation and visualization excluded. Relative output is not metric geometry, appearance improvement or live performance.'
        report['visualization']='Independent per-image min/max to grayscale, white larger relative-depth output. No calibrated distance scale; do not compare grayscale brightness across views.'
        report['status']='completed'
    except Exception as error:
        report['status']='failed';report['error']=repr(error);report['traceback']=traceback.format_exc()
        raise
    finally:
        write_json(out/'report.json',report)
        print(json.dumps({'status':report['status'],'error':report.get('error'),'images':report['images']},indent=2))


if __name__=='__main__':main()
