"""Paired offline DCE temporal diagnostic with native parity and failure controls."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json


def stats(values):
    a = np.asarray(values, np.float64)
    return {'count':len(a), 'min':float(a.min()), 'median':float(np.median(a)),
            'p95':float(np.percentile(a,95)), 'p99':float(np.percentile(a,99)), 'max':float(a.max())}


def smooth(a,b,x):
    t = np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)


def curves(rgb, model):
    x = torch.from_numpy(rgb.astype(np.float32)/255).permute(2,0,1)[None]
    x = F.interpolate(x, size=(180,320), mode='bilinear', align_corners=False)
    with torch.inference_mode():
        _, r = model(x)
    return r[0].numpy()


def compose(rgb, curve, strength):
    c = rgb.astype(np.float32)/255
    h,w = c.shape[:2]
    r = cv2.resize(curve.transpose(1,2,0), (w,h), interpolation=cv2.INTER_LINEAR)
    invalid = (~np.isfinite(r)).any(2) | (np.abs(r)>1).any(2)
    r = np.nan_to_num(r)
    full = c.copy()
    for _ in range(8):
        full += r*(full*full-full)
    coeff = np.array([.2126,.7152,.0722], np.float32)
    l = np.sum(c*coeff,axis=2)
    target = np.sum(full*coeff,axis=2)
    gain = np.clip(target/np.maximum(l,.001),.85,1.4)
    cap = .06/np.maximum(c.max(2),.001)
    delta = np.clip((gain-1)*strength,-cap,cap)
    protect = smooth(.03,.10,l)*(1-smooth(.70,.90,l))
    yy = (np.arange(h,dtype=np.float32)+.5)/h
    xx = (np.arange(w,dtype=np.float32)+.5)/w
    protect *= (smooth(.045,.10,yy)*(1-smooth(.84,.91,yy)))[:,None]
    crosshair = np.maximum(np.abs(xx[None,:]-.5)/.018,np.abs(yy[:,None]-.5)/.025)
    protect *= smooth(1,2,crosshair)
    protect[invalid] = 0
    result = c*(1+delta*protect)[:,:,None]
    return np.rint(np.clip(result,0,1)*255).astype(np.uint8)


def correspondence(previous, current, config):
    parameters = tuple(config['parameters'])
    forward = cv2.calcOpticalFlowFarneback(previous,current,None,*parameters)
    backward = cv2.calcOpticalFlowFarneback(current,previous,None,*parameters)
    h,w = current.shape
    yy,xx = np.mgrid[:h,:w].astype(np.float32)
    mx = xx+backward[:,:,0]; my = yy+backward[:,:,1]
    remap = lambda a: cv2.remap(a,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    closure = np.linalg.norm(backward+remap(forward),axis=2)
    photo = np.abs(current.astype(np.float32)-remap(previous).astype(np.float32))
    grad = np.hypot(cv2.Sobel(current,cv2.CV_32F,1,0),cv2.Sobel(current,cv2.CV_32F,0,1))
    core = (xx>=w*.05)&(xx<w*.95)&(yy>=h*.10)&(yy<h*.84)&~((np.abs(xx-w*.5)<w*.036)&(np.abs(yy-h*.5)<h*.05))
    valid = core&(mx>=0)&(mx<w-1)&(my>=0)&(my<h-1)&(closure<=config['maximum_closure_px'])&(photo<=config['maximum_source_gray_error_codes'])&(grad>config['minimum_sobel_magnitude'])
    return mx,my,valid,{'valid_pixels':int(valid.sum()),'core_pixels':int(core.sum()),'coverage':float(valid.sum()/core.sum())}


def metric(previous,current,mx,my,valid):
    moved = cv2.remap(previous,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
    values = np.abs(current-moved)[valid]
    return {'median_codes':float(np.median(values)) if len(values) else None,
            'p95_codes':float(np.percentile(values,95)) if len(values) else None,
            'max_codes':float(values.max()) if len(values) else None}


def read_exact(stream,count):
    chunks = []
    while count:
        block = stream.read(count)
        if not block:
            raise EOFError('Decoder ended early')
        chunks.append(block); count -= len(block)
    return b''.join(chunks)


def summarize(rows,gates):
    result = {}
    for split in ('selection','reserved'):
        chosen = [r for r in rows if r['split']==split and 'correspondence' in r]
        coverage = stats([r['correspondence']['coverage'] for r in chosen])
        result[split] = {'coverage':coverage,'controls':{}}
        for mode in ('enhancement','identity','alternating'):
            values = [r[mode] for r in chosen]
            valid = all(v['median_codes'] is not None for v in values)
            med = stats([v['median_codes'] for v in values]) if valid else None
            tail = stats([v['p95_codes'] for v in values]) if valid else None
            passed = valid and coverage['median']>=gates['median_coverage_min'] and med['p95']<=gates['p95_of_frame_median_codes_max'] and tail['p95']<=gates['p95_of_frame_p95_codes_max']
            result[split]['controls'][mode] = {'frame_median':med,'frame_p95':tail,'passes_coarse_gates':bool(passed)}
    return result


def main():
    native_replay = '--native-replay' in sys.argv
    out = ROOT / ('runs/dce-temporal-native-v2' if native_replay else 'runs/dce-temporal-v1')
    plan_path = ROOT / ('scenes/playable-dce-temporal-native-v2.json' if native_replay else 'scenes/playable-dce-temporal-v1.json')
    plan = json.loads(plan_path.read_text())
    if (out/'report.json').exists():
        raise FileExistsError('Retain previous attempt; do not overwrite')
    shutil.copyfile(__file__,out/'driver.py')
    report = {'schema_version':1,'status':'started','started_at':datetime.now(timezone.utc).isoformat(),
              'plan_sha256':digest(plan_path),'driver_sha256':digest(Path(__file__)), 'frames':[]}
    write_json(out/'report.json',report)
    decoder = None; replay = None
    deadline = datetime.fromisoformat(plan['deadline'])
    try:
        for name,sha in plan['source_hashes'].items():
            if digest(ROOT/name)!=sha:
                raise ValueError('Changed pinned input: '+name)
        active = subprocess.check_output(['powershell','-NoProfile','-Command','Get-Process -Name ArmaReforgerSteam,ArmaReforgerWorkbenchSteamDiag,enr_companion -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName; exit 0'],text=True).strip()
        if active:
            raise ValueError('Experiment sessions active')
        torch.set_num_threads(4); cv2.setNumThreads(4)
        model_dir = ROOT/'runs/pretrained/zero-dce-plusplus'
        spec = importlib.util.spec_from_file_location('pinned_dce',model_dir/'model.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        model = module.enhance_net_nopool(1).eval()
        model.load_state_dict(torch.load(model_dir/'Epoch99.pth',map_location='cpu',weights_only=True),strict=True)
        snapshot = ROOT/plan['parity_snapshot']
        rgb = np.array(Image.open(snapshot/'source.bmp').convert('RGB'))
        actual = np.array(Image.open(snapshot/'output.bmp').convert('RGB'))
        native = np.fromfile(snapshot/'curve.f32',dtype='<f4').reshape(3,180,320)
        predicted = curves(rgb,model)
        composed = compose(rgb,predicted,plan['strength'])
        error = np.abs(predicted-native)
        codes = np.abs(composed.astype(np.int16)-actual.astype(np.int16))
        gate = plan['parity_gates']
        parity = {'curve_max':float(error.max()),'curve_mean':float(error.mean()),
                  'rgb8_max':int(codes.max()),'rgb8_mean':float(codes.mean()),'rgb8_p99':float(np.percentile(codes,99)),
                  'curve_values':int(error.size),'rgb8_channels':int(codes.size)}
        parity['passes'] = bool(error.max()<=gate['curve_max_absolute_error'] and codes.max()<=gate['composed_rgb8_max_error'] and codes.mean()<=gate['composed_rgb8_mean_error'])
        np.save(out/'parity-cpu-curve.npy',predicted)
        Image.fromarray(composed).save(out/'parity-cpu-output.png')
        if native_replay:
            report['original_cpu_reproduction']=parity.copy()
            native_log=(out/'native.log').open('wb')
            replay=subprocess.Popen([str(ROOT/'build/Release/enr_dce_replay.exe'),str(model_dir/'weights.bin'),str(out/'companion.hlsl'),str(out/'native-curves')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=native_log)
            replay.stdin.write(rgb.tobytes()); replay.stdin.flush()
            native_rgb=np.frombuffer(read_exact(replay.stdout,rgb.size),np.uint8).reshape(rgb.shape)
            native_curve=np.fromfile(out/'native-curves/curve-000000.f32',dtype='<f4').reshape(3,180,320)
            native_error=np.abs(native_curve-native)
            native_codes=np.abs(native_rgb.astype(np.int16)-actual.astype(np.int16))
            parity={'curve_max':float(native_error.max()),'curve_mean':float(native_error.mean()),
                    'rgb8_max':int(native_codes.max()),'rgb8_mean':float(native_codes.mean()),'rgb8_p99':float(np.percentile(native_codes,99)),
                    'curve_values':int(native_error.size),'rgb8_channels':int(native_codes.size),
                    'independent_cpu_curve_max':float(np.abs(native_curve-predicted).max())}
            parity['passes']=bool(native_error.max()<=gate['curve_max_absolute_error'] and native_codes.max()<=gate['composed_rgb8_max_error'] and native_codes.mean()<=gate['composed_rgb8_mean_error'] and parity['independent_cpu_curve_max']<=gate['curve_max_absolute_error'])
            Image.fromarray(native_rgb).save(out/'parity-native-output.png')
            report['reproduction_mode']='Native D3D11 offscreen, full upload/readback; no capture/Present'
        write_json(out/'parity.json',parity); report['parity']=parity
        print(json.dumps({'parity':parity}),flush=True)
        if not parity['passes']:
            raise ValueError('Native reproduction gate failed; stop without processing the segment')
        probe = json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height:frame=best_effort_timestamp_time','-of','json',str(ROOT/plan['source'])]))
        if [probe['streams'][0]['width'],probe['streams'][0]['height']]!=plan['source_dimensions']:
            raise ValueError('Wrong video dimensions')
        begin,end = plan['segment_seconds']
        pts = np.array([float(f['best_effort_timestamp_time']) for f in probe['frames']])
        pts = pts[(pts>=begin)&(pts<end)]
        retained = np.array(json.loads((ROOT/'runs/depth-motion-v1/source-timestamps.json').read_text()))
        if not np.array_equal(pts,retained) or len(pts)!=600 or np.any(np.diff(pts)<=0):
            raise ValueError('Source timestamps changed')
        write_json(out/'source-timestamps.json',pts.tolist())
        report['source_intervals_ms']=stats(np.diff(pts)*1000)
        (out/'frames').mkdir()
        predictions = np.lib.format.open_memmap(out/'curves.npy',mode='w+',dtype=np.float32,shape=(len(pts),3,180,320))
        residuals = np.lib.format.open_memmap(out/'residuals.npy',mode='w+',dtype=np.float32,shape=(len(pts),252,448))
        command = ['ffmpeg','-hide_banner','-loglevel','error','-threads','2','-i',str(ROOT/plan['source']),'-vf',f'select=gte(t\\,{begin})*lt(t\\,{end})','-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
        report['decoder_command']=['<REPOSITORY>' if part==str(ROOT) else part.replace(str(ROOT),'.') for part in command]
        log = (out/'decoder.log').open('wb')
        decoder = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=log)
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
        coeff = np.array([.2126,.7152,.0722],np.float32)
        previous = None; previous_residual = None; previous_alternating = None
        zero = np.zeros((252,448),np.float32)
        concat = ['ffconcat version 1.0']; keys = {0,180,420,599}
        for index,timestamp in enumerate(pts):
            if datetime.now(timezone.utc)>deadline:
                raise TimeoutError('Declared 30-minute diagnostic deadline exceeded')
            raw = read_exact(decoder.stdout,2560*1440*3)
            rgb = np.frombuffer(raw,np.uint8).reshape(1440,2560,3)
            start = time.perf_counter()
            if native_replay:
                replay.stdin.write(raw); replay.stdin.flush()
                y=np.frombuffer(read_exact(replay.stdout,len(raw)),np.uint8).reshape(rgb.shape)
                r=np.fromfile(out/'native-curves'/f'curve-{index+1:06d}.f32',dtype='<f4').reshape(3,180,320)
            else:
                r = curves(rgb,model)
                y = compose(rgb,r,plan['strength'])
            reproduction_ms = (time.perf_counter()-start)*1000
            if not np.isfinite(r).all():
                raise ValueError('Nonfinite curve')
            predictions[index]=r
            residual = cv2.resize(np.sum((y.astype(np.float32)-rgb)*coeff,axis=2),(448,252),interpolation=cv2.INTER_AREA)
            residuals[index]=residual
            alternating_rgb = np.clip(rgb.astype(np.int16)+(8 if index%2 else -8),0,255)
            alternating = cv2.resize(np.sum((alternating_rgb-rgb)*coeff,axis=2),(448,252),interpolation=cv2.INTER_AREA)
            small = cv2.resize(rgb,(448,252),interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(small,cv2.COLOR_RGB2GRAY)
            row = {'index':index,'source_pts_s':float(timestamp),'relative_pts_s':float(timestamp-pts[0]),
                   'split':'reserved' if timestamp>=plan['reserved_start_seconds'] else 'selection',
                   'source_rgb8_sha256':hashlib.sha256(raw).hexdigest(),
                   'enhanced_rgb8_sha256':hashlib.sha256(y.tobytes()).hexdigest(),
                   'processing_roundtrip_ms':reproduction_ms,'curve_min':float(r.min()),'curve_max':float(r.max()),
                   'max_rgb8_change':int(np.abs(y.astype(np.int16)-rgb).max()),
                   'newly_clipped_channels':int((((y==0)|(y==255))&((rgb>0)&(rgb<255))).sum())}
            if previous is not None:
                mx,my,valid,coverage = correspondence(previous,gray,plan['correspondence'])
                row['correspondence']=coverage
                row['enhancement']=metric(previous_residual,residual,mx,my,valid)
                row['identity']=metric(zero,zero,mx,my,valid)
                row['alternating']=metric(previous_alternating,alternating,mx,my,valid)
            previous=gray; previous_residual=residual; previous_alternating=alternating
            canvas = Image.new('RGB',(1792,536),'#101820')
            canvas.paste(Image.fromarray(cv2.resize(rgb,(896,504),interpolation=cv2.INTER_AREA)),(0,32))
            canvas.paste(Image.fromarray(cv2.resize(y,(896,504),interpolation=cv2.INTER_AREA)),(896,32))
            draw = ImageDraw.Draw(canvas)
            draw.text((12,5),f'Same-frame source | {timestamp-begin:.3f}s | 1x speed',font=font,fill='white')
            draw.text((908,5),f'DCE {"native replay" if native_replay else "CPU reproduction"} | {row["split"]} | unchanged model',font=font,fill='white')
            path = out/'frames'/f'{index:04d}.png'; canvas.save(path,compress_level=1)
            row['comparison_png_sha256']=digest(path)
            duration = float(pts[index+1]-timestamp) if index+1<len(pts) else float(end-timestamp)
            concat.extend([f"file 'frames/{index:04d}.png'",'option framerate 60',f'duration {duration:.9f}'])
            if index in keys:
                Image.fromarray(rgb).save(out/f'key-{index:04d}-source.png')
                Image.fromarray(y).save(out/f'key-{index:04d}-enhanced.png')
                original = np.array(Image.open(ROOT/'runs/depth-motion-v1'/f'key-{index:04d}-source.png').convert('RGB'))
                row['matches_retained_depth_source_pixels']=bool(np.array_equal(rgb,original))
                if not row['matches_retained_depth_source_pixels']:
                    raise ValueError('Decoded source key differs from retained CPU decode')
            report['frames'].append(row)
            if index%60==0:
                write_json(out/'report.json',report)
                print(json.dumps({'frame':index,'reproduction_ms':reproduction_ms,'source_pts_s':float(timestamp)}),flush=True)
        predictions.flush(); residuals.flush(); del predictions,residuals
        if decoder.stdout.read(1):
            raise ValueError('Unexpected extra decoded data')
        if decoder.wait(timeout=30)!=0:
            raise ValueError('Decoder failed')
        decoder=None; log.close()
        if replay is not None:
            replay.stdin.close()
            if replay.stdout.read(1) or replay.wait(timeout=30)!=0:
                raise ValueError('Native replay stream failed')
            replay=None; native_log.close()
            report['native_log']=(out/'native.log').read_text()
            if 'adapter=AMD Radeon RX 7800 XT' not in report['native_log'] or 'completed_frames=601' not in report['native_log']:
                raise ValueError('Native replay adapter/frame count differs')
        (out/'frames.ffconcat').write_text('\n'.join(concat)+'\n')
        report['summary']=summarize(report['frames'],plan['gates'])
        report['sensitivity_controls_pass']=all(s['controls']['identity']['passes_coarse_gates'] and not s['controls']['alternating']['passes_coarse_gates'] for s in report['summary'].values())
        report['enhancement_passes_coarse_gates']=all(s['controls']['enhancement']['passes_coarse_gates'] for s in report['summary'].values())
        report['processing_roundtrip_ms']=stats([r['processing_roundtrip_ms'] for r in report['frames']])
        report['retained_hashes']={name:digest(out/name) for name in ['curves.npy','residuals.npy','source-timestamps.json','frames.ffconcat','parity.json','parity-cpu-curve.npy','parity-cpu-output.png']}
        report['status']='completed'
    except Exception:
        report['status']='failed'; report['error']=traceback.format_exc()
        raise
    finally:
        if decoder is not None and decoder.poll() is None:
            decoder.terminate(); decoder.wait(timeout=10)
        if replay is not None and replay.poll() is None:
            replay.terminate(); replay.wait(timeout=10)
        report['ended_at']=datetime.now(timezone.utc).isoformat()
        report['minutes_since_plan_start']=(datetime.now(timezone.utc)-datetime.fromisoformat(plan['started_at'])).total_seconds()/60
        write_json(out/'report.json',report)
        print(json.dumps({k:report[k] for k in ['status','minutes_since_plan_start']}),flush=True)


if __name__ == '__main__':
    main()
