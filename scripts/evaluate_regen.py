"""Bounded evaluation of the unchanged author REGEN generator on CPU/DirectML.

The author's implementation and licenses are retained under runs/pretrained/regen.
This file evaluates captured images; it does not change the live companion.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import time

import numpy as np
from PIL import Image
import torch
import onnxruntime as ort

ROOT=Path(__file__).resolve().parents[1]
CHECKPOINT_SHA='46258537fb99b04c9bc891691361f38c59f3fdff79ee9f495e69402aa58c6a69'


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): digest.update(chunk)
    return digest.hexdigest()


def save(x,path):
    image=((x[0].transpose(1,2,0)+1)*127.5).clip(0,255).astype(np.uint8)
    Image.fromarray(image).save(path)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--width',type=int,default=960)
    p.add_argument('--height',type=int,default=544)
    p.add_argument('--samples',type=int,default=5)
    a=p.parse_args(); out=a.out.resolve(); out.mkdir(parents=True,exist_ok=False)
    if a.width%32 or a.height%32: raise ValueError('Use dimensions divisible by 32')
    source=ROOT/'runs/pretrained/regen'; checkpoint=source/'gta2cityscapes.pth'
    if sha(checkpoint)!=CHECKPOINT_SHA: raise ValueError('Checkpoint hash mismatch')
    plan=json.loads((ROOT/'scenes/playable-rgb-evaluation-v2.json').read_text())
    adapters=[json.loads(line) for line in subprocess.check_output([str(ROOT/'build/Release/enr_adapter_info.exe')],text=True).splitlines()]
    adapter=next(x for x in adapters if x['description']=='AMD Radeon RX 7800 XT' and not x['software'])
    report={'schema_version':1,'status':'started','candidate':'REGEN GTA2Cityscapes','dimensions':[a.width,a.height],
            'checkpoint_sha256':CHECKPOINT_SHA,'source_hashes':{str(f.relative_to(source)).replace('\\','/'):sha(f) for f in source.rglob('*.py')},
            'plan_sha256':sha(ROOT/'scenes/playable-rgb-evaluation-v2.json'),'adapter':adapter,'runtime':ort.__version__,'torch':torch.__version__,
            'precision':'FP32','scope':'Synchronized Python ONNX Runtime call, including CPU-input upload and output readback. File decode, resize, model initialization and PNG encoding excluded. Game is not running; not complete application FPS.',
            'preprocessing':'Pillow bilinear resize to declared dimensions, RGB float32 mapped from 0..255 to -1..1, NCHW. Author normalization; resize uses Pillow instead of OpenCV.',
            'images':[]}
    (out/'report.json').write_text(json.dumps(report,indent=2))
    try:
        torch.set_num_threads(4)
        spec=importlib.util.spec_from_file_location('regen_author_generator',source/'onnx_utils/generator.py')
        author=importlib.util.module_from_spec(spec); spec.loader.exec_module(author)
        model=author.GlobalGenerator(3,3,64,4,9,author.get_norm_layer('instance')).eval()
        state=torch.load(checkpoint,map_location='cpu',weights_only=True)
        if 'state_dict' in state: state=state['state_dict']
        model.load_state_dict(state,strict=True); del state
        report['parameters']=sum(p.numel() for p in model.parameters())
        print('Loaded',report['parameters'],'parameters on CPU',flush=True)
        inputs=[]
        for rel in plan['inputs']:
            file=ROOT/rel
            im=Image.open(file).convert('RGB').resize((a.width,a.height),Image.Resampling.BILINEAR)
            x=np.ascontiguousarray((np.asarray(im,dtype=np.float32)/127.5-1).transpose(2,0,1)[None])
            inputs.append((file,x))
        x0=torch.from_numpy(inputs[0][1])
        with torch.inference_mode():
            began=time.perf_counter(); reference=model(x0).numpy(); report['cpu_reference_ms']=(time.perf_counter()-began)*1000
            np.save(out/'cpu-reference.npy',reference); save(reference,out/'cpu-reference.png')
            print('CPU reference:',round(report['cpu_reference_ms'],2),'ms',flush=True)
            began=time.perf_counter()
            torch.onnx.export(model,x0,str(out/'model.onnx'),opset_version=17,input_names=['input'],output_names=['output'],dynamo=False,do_constant_folding=True)
            report['export_ms']=(time.perf_counter()-began)*1000
        del model
        report['onnx_sha256']=sha(out/'model.onnx')
        print('ONNX exported; creating DirectML session',flush=True)
        options=ort.SessionOptions(); options.enable_mem_pattern=False; options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
        options.enable_profiling=True; options.profile_file_prefix=str(out/'ort-profile')
        options.add_session_config_entry('session.disable_cpu_ep_fallback','1')
        began=time.perf_counter()
        session=ort.InferenceSession(str(out/'model.onnx'),sess_options=options,providers=[('DmlExecutionProvider',{'device_id':str(adapter['index'])})])
        report['session_setup_ms']=(time.perf_counter()-began)*1000
        report['providers']=session.get_providers(); session.disable_fallback()
        for i,(file,x) in enumerate(inputs):
            output=session.run(['output'],{'input':x})[0] # warmup, synchronized CPU output
            timings=[]
            for n in range(a.samples):
                began=time.perf_counter(); output=session.run(['output'],{'input':x})[0]; timings.append((time.perf_counter()-began)*1000)
            if not np.isfinite(output).all(): raise ValueError('Nonfinite model output')
            save(x,out/f'{i:02d}-source-input.png'); save(output,out/f'{i:02d}-raw-model.png')
            np.save(out/f'{i:02d}-raw-model.npy',output)
            raw=Image.open(out/f'{i:02d}-raw-model.png'); raw.resize(Image.open(file).size,Image.Resampling.BILINEAR).save(out/f'{i:02d}-raw-upscaled.png')
            item={'source':str(file.relative_to(ROOT)).replace('\\','/'),'source_sha256':sha(file),'timings_ms':timings,'median_ms':float(np.median(timings)),
                  'raw_max_abs_rgb_change':float(abs(output-x).max()/2),'raw_mean_abs_rgb_change':float(abs(output-x).mean()/2),
                  'range_min':float(output.min()),'range_max':float(output.max()),'raw_sha256':sha(out/f'{i:02d}-raw-model.npy')}
            if i==0:
                delta=abs(output-reference)
                report['cpu_dml_parity']={'max_abs':float(delta.max()),'mean_abs':float(delta.mean()),'limits':{'max_abs':.01,'mean_abs':.001},'passed':bool(delta.max()<=.01 and delta.mean()<=.001)}
            report['images'].append(item)
            print(json.dumps(item),flush=True)
        profile=Path(session.end_profiling()); report['profile_file']=profile.name
        events=json.loads(profile.read_text())
        providers={}
        for event in events:
            provider=event.get('args',{}).get('provider')
            if provider: providers[provider]=providers.get(provider,0)+1
        report['profile_provider_events']=providers
        if not report['cpu_dml_parity']['passed']: raise ValueError('CPU/DirectML parity failed')
        report['status']='completed'
    except Exception as e:
        report.update(status='failed',error=repr(e)); raise
    finally:
        (out/'report.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__': main()
