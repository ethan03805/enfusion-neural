"""Bounded, timestamp-preserving offline RGB depth motion diagnostic."""
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
from PIL import Image, ImageDraw, ImageFont
import torch
import torch.nn.functional as F

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr.references import digest,write_json


def stats(values):
    a=np.asarray(values)
    return {'count':len(a),'median':float(np.median(a)),'p95':float(np.percentile(a,95)),
        'p99':float(np.percentile(a,99)),'max':float(a.max()),'min':float(a.min())}


def read_exact(stream,count):
    chunks=[]
    while count:
        block=stream.read(count)
        if not block:raise EOFError('Decoder ended before all declared frames')
        chunks.append(block);count-=len(block)
    return b''.join(chunks)


def correspondence(previous_gray,current_gray,previous_depth,current_depth,scale):
    params=(.5,3,15,3,5,1.2,0)
    forward=cv2.calcOpticalFlowFarneback(previous_gray,current_gray,None,*params)
    backward=cv2.calcOpticalFlowFarneback(current_gray,previous_gray,None,*params)
    h,w=current_gray.shape;yy,xx=np.mgrid[:h,:w].astype(np.float32)
    mx=xx+backward[:,:,0];my=yy+backward[:,:,1]
    remap=lambda a:cv2.remap(a,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    closure=np.linalg.norm(backward+remap(forward),axis=2)
    photo=np.abs(current_gray.astype(np.float32)-remap(previous_gray).astype(np.float32))
    dx=cv2.Sobel(current_gray,cv2.CV_32F,1,0);dy=cv2.Sobel(current_gray,cv2.CV_32F,0,1)
    core=(xx>=w*.05)&(xx<w*.95)&(yy>=h*.05)&(yy<h*.8)&~((np.abs(xx-w*.5)<w*.025)&(np.abs(yy-h*.5)<h*.025))
    valid=core&(mx>=0)&(mx<w-1)&(my>=0)&(my<h-1)&(closure<=1)&(photo<=12)&(np.hypot(dx,dy)>5)
    delta=np.abs(current_depth-remap(previous_depth))/scale
    values=delta[valid]
    return {'valid_pixels':int(valid.sum()),'core_pixels':int(core.sum()),'coverage':float(valid.sum()/core.sum()),
        'median_normalized_change':float(np.median(values)) if len(values) else None,
        'p95_normalized_change':float(np.percentile(values,95)) if len(values) else None}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    (out/'frames').mkdir();shutil.copyfile(__file__,out/'driver.py')
    plan_path=ROOT/'scenes/playable-depth-motion-v1.json';plan=json.loads(plan_path.read_text())
    report={'schema_version':1,'status':'started','started_at':datetime.now(timezone.utc).isoformat(),
        'plan_sha256':digest(plan_path),'driver_sha256':digest(Path(__file__)),'frames':[]}
    write_json(out/'report.json',report);decoder=None
    try:
        source=ROOT/plan['source']
        if digest(source)!=plan['source_sha256']:raise ValueError('Source video changed')
        report['source']=plan['source'];report['source_sha256']=digest(source)
        active=subprocess.check_output(['powershell','-NoProfile','-Command','Get-Process -Name ArmaReforgerSteam,ArmaReforgerWorkbenchSteamDiag,enr_companion -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName; exit 0'],text=True).strip()
        if active:raise ValueError('GPU sessions active: '+active)
        report['adapter_info']=subprocess.check_output([str(ROOT/'build/Release/enr_adapter_info.exe')],text=True)
        if json.loads(report['adapter_info'].splitlines()[0])['description']!='AMD Radeon RX 7800 XT':raise ValueError('Unexpected adapter 0')
        provenance_path=ROOT/'runs/pretrained/depth-anything-v2-small-v1/source.json';provenance=json.loads(provenance_path.read_text())
        for path,sha in provenance['source_hashes'].items():
            if digest(ROOT/path)!=sha:raise ValueError('Changed author source')
        checkpoint=provenance_path.parent/'depth_anything_v2_vits.pth'
        if digest(checkpoint)!=provenance['checkpoint_sha256']:raise ValueError('Changed checkpoint')
        report['provenance_sha256']=digest(provenance_path)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,time_base:frame=best_effort_timestamp_time','-of','json',str(source)]))
        write_json(out/'source-probe.json',probe);report['source_probe_sha256']=digest(out/'source-probe.json')
        width=probe['streams'][0]['width'];height=probe['streams'][0]['height']
        if (width,height)!=(2560,1440):raise ValueError('Unexpected source dimensions')
        begin,end=plan['segment_seconds']
        pts=np.array([float(f['best_effort_timestamp_time']) for f in probe['frames']])
        pts=pts[(pts>=begin)&(pts<end)]
        if len(pts)<250 or len(pts)>650 or np.any(np.diff(pts)<=0):raise ValueError('Invalid selected timestamps')
        write_json(out/'source-timestamps.json',pts.tolist())
        report['source_intervals_ms']=stats(np.diff(pts)*1000);report['frame_count']=len(pts)
        torch.set_num_threads(8);cv2.setNumThreads(8);torch.manual_seed(0)
        sys.path.insert(0,str(ROOT/'runs/pretrained/depth-anything-v2-source-v1'))
        from depth_anything_v2.dpt import DepthAnythingV2
        model=DepthAnythingV2(encoder='vits',features=64,out_channels=[48,96,192,384]).eval()
        model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True),strict=True)
        decoder_args=['ffmpeg','-hide_banner','-loglevel','error','-threads','2','-i',str(source),'-vf',f'select=gte(t\\,{begin})*lt(t\\,{end})','-fps_mode','passthrough','-f','rawvideo','-pix_fmt','bgr24','pipe:1']
        report['decoder_command']=decoder_args
        decoder_log=(out/'decoder.log').open('wb')
        decoder=subprocess.Popen(decoder_args,stdout=subprocess.PIPE,stderr=decoder_log)
        session=None;previous_gray=None;previous_depth=None;records=[];concat=['ffconcat version 1.0']
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
        key_indices={0,min(range(len(pts)),key=lambda j:abs(pts[j]-begin-3)),min(range(len(pts)),key=lambda j:abs(pts[j]-begin-7)),len(pts)-1}
        for i,timestamp in enumerate(pts):
            raw=np.frombuffer(read_exact(decoder.stdout,width*height*3),np.uint8).reshape(height,width,3)
            start=time.perf_counter();tensor,_=model.image2tensor(raw,252);x=tensor.cpu().contiguous().numpy()
            preprocess_ms=(time.perf_counter()-start)*1000
            if i==0:
                report['tensor_shape']=list(x.shape)
                if x.shape!=(1,3,252,448):raise ValueError('Unexpected static shape')
                np.save(out/'first-input.npy',x)
                with torch.inference_mode():cpu=model(torch.from_numpy(x)).numpy()
                np.save(out/'first-cpu.npy',cpu)
                graph=out/'model.onnx'
                torch.onnx.export(model,torch.from_numpy(x),str(graph),opset_version=17,input_names=['rgb'],output_names=['relative_depth'],do_constant_folding=True,dynamo=False)
                onnx.checker.check_model(onnx.load(graph));report['onnx_sha256']=digest(graph)
                options=ort.SessionOptions();options.enable_mem_pattern=False;options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
                options.add_session_config_entry('session.disable_cpu_ep_fallback','1');options.enable_profiling=True;options.profile_file_prefix=str(out/'profile')
                session=ort.InferenceSession(str(graph),sess_options=options,providers=[('DmlExecutionProvider',{'device_id':0})]);session.disable_fallback()
                for _ in range(5):session.run(None,{'rgb':x})
                predictions=np.lib.format.open_memmap(out/'predictions.npy',mode='w+',dtype=np.float32,shape=(len(pts),252,448))
            start=time.perf_counter();prediction=session.run(None,{'rgb':x})[0][0]
            model_ms=(time.perf_counter()-start)*1000
            if not np.isfinite(prediction).all():raise ValueError('Nonfinite prediction')
            predictions[i]=prediction
            if i==0:
                error=np.abs(prediction-cpu[0]);scale=max(float(np.ptp(cpu)),1e-6)
                report['parity']={'raw_max':float(error.max()),'raw_mean':float(error.mean()),'cpu_range':scale,
                    'normalized_max':float(error.max())/scale,'normalized_mean':float(error.mean())/scale,
                    'passed':bool(error.max()/scale<=.001 and error.mean()/scale<=.0001)}
                if not report['parity']['passed']:raise ValueError('CPU parity failed')
                low=float(prediction.min());high=float(prediction.max());fixed_range=max(high-low,1e-6)
                report['fixed_visualization_range']=[low,high]
            small=cv2.resize(raw,(448,252),interpolation=cv2.INTER_AREA);gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
            row={'index':i,'source_pts_s':float(timestamp),'relative_pts_s':float(timestamp-pts[0]),
                'split':'reserved' if timestamp>=plan['reserved_start_seconds'] else 'selection',
                'input_sha256':__import__('hashlib').sha256(x.tobytes()).hexdigest(),
                'preprocess_ms':preprocess_ms,'model_ms':model_ms,'output_min':float(prediction.min()),'output_max':float(prediction.max()),
                'outside_first_range_fraction':float(np.mean((prediction<low)|(prediction>high)))}
            if i>0:row['correspondence']=correspondence(previous_gray,gray,previous_depth,prediction,fixed_range)
            previous_gray=gray;previous_depth=prediction.copy()
            visual=np.rint(np.clip((prediction-low)/fixed_range,0,1)*255).astype(np.uint8)
            canvas=Image.new('RGB',(1792,536),'#101820')
            canvas.paste(Image.fromarray(cv2.cvtColor(cv2.resize(raw,(896,504),interpolation=cv2.INTER_AREA),cv2.COLOR_BGR2RGB)),(0,32))
            canvas.paste(Image.fromarray(cv2.resize(visual,(896,504),interpolation=cv2.INTER_LINEAR)).convert('RGB'),(896,32))
            draw=ImageDraw.Draw(canvas)
            draw.text((12,5),f'Reduced Reforger RGB | source {timestamp:.3f}s | 1x speed',fill='white',font=font)
            draw.text((908,5),f'Relative depth | fixed first-frame range | {row["split"]}',fill='white',font=font)
            frame_path=out/'frames'/f'{i:04d}.png';canvas.save(frame_path,compress_level=2)
            duration=float(pts[i+1]-timestamp) if i+1<len(pts) else float(end-timestamp)
            concat.extend([f"file 'frames/{i:04d}.png'",'option framerate 60',f'duration {duration:.9f}'])
            if i in key_indices:
                Image.fromarray(cv2.cvtColor(raw,cv2.COLOR_BGR2RGB)).save(out/f'key-{i:04d}-source.png')
                with torch.inference_mode():full=F.interpolate(torch.from_numpy(prediction)[None,None],(height,width),mode='bilinear',align_corners=True)[0,0].numpy()
                Image.fromarray(np.rint(np.clip((full-low)/fixed_range,0,1)*255).astype(np.uint8)).save(out/f'key-{i:04d}-depth.png')
            records.append(row)
            if i%100==0:print(json.dumps({'frame':i,'source_pts_s':timestamp,'model_ms':model_ms}),flush=True)
        predictions.flush();del predictions
        if decoder.stdout.read(1):raise ValueError('More decoded frames than source timestamps')
        if decoder.wait(timeout=30)!=0:raise ValueError('Decoder failed')
        decoder_log.close();decoder=None
        profile=Path(session.end_profiling())
        report['profile_file']=profile.name;report['profile_sha256']=digest(profile)
        report['profile_provider_events']=dict(Counter(e.get('args',{}).get('provider') for e in json.loads(profile.read_text()) if e.get('args',{}).get('provider')))
        if set(report['profile_provider_events'])!={'DmlExecutionProvider'}:raise ValueError('CPU execution events present')
        report['frames']=records;report['model_ms']=stats([r['model_ms'] for r in records]);report['preprocess_ms']=stats([r['preprocess_ms'] for r in records])
        report['provisional_cost_pass']=report['model_ms']['p95']<=plan['provisional_p95_call_limit_ms']
        report['diagnostics']={}
        limits=plan['motion_diagnostic_limits']
        for split in ['selection','reserved']:
            rows=[r['correspondence'] for r in records if r['split']==split and 'correspondence' in r]
            available=[r for r in rows if r['median_normalized_change'] is not None]
            d={k:stats([r[k] for r in available]) for k in ['coverage','median_normalized_change','p95_normalized_change']}
            d['frames_without_valid_correspondence']=len(rows)-len(available)
            d['numeric_limits_pass']=bool(d['coverage']['median']>=limits['median_coverage_min'] and d['median_normalized_change']['p95']<=limits['p95_of_frame_median_normalized_change'] and d['p95_normalized_change']['p95']<=limits['p95_of_frame_p95_normalized_change'])
            report['diagnostics'][split]=d
        concat.extend([f"file 'frames/{len(pts)-1:04d}.png'",'option framerate 60'])
        (out/'frames.ffconcat').write_text('\n'.join(concat)+'\n',encoding='utf-8')
        report['key_indices']=sorted(key_indices);report['predictions_sha256']=digest(out/'predictions.npy')
        report['first_input_sha256']=digest(out/'first-input.npy');report['first_cpu_sha256']=digest(out/'first-cpu.npy')
        report['status']='inference_completed'
    except Exception as error:
        report.update(status='failed',error=repr(error),traceback=traceback.format_exc());raise
    finally:
        if decoder and decoder.poll() is None:decoder.terminate();decoder.wait(timeout=10)
        report['finished_at']=datetime.now(timezone.utc).isoformat()
        write_json(out/'report.json',report)
        print(json.dumps({k:v for k,v in report.items() if k not in ['frames','decoder_command','traceback']},indent=2))


if __name__=='__main__':main()
