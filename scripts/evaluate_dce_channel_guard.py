"""Validate a single headroom guard against the failed native replay and fixtures."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr.references import digest,write_json
from enr.exposure_guard import compose_constant_curve
from scripts.evaluate_dce_temporal import read_exact,curves,correspondence,metric,summarize,stats


class Replay:
    def __init__(self,out,shader,weights):
        self.folder=out; out.mkdir(exist_ok=False)
        self.log=(out/'native.log').open('wb')
        self.p=subprocess.Popen([str(ROOT/'runs/dce-channel-guard-v1/enr_dce_replay.exe'),str(weights),str(shader),str(out/'curves')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log)
        self.index=0

    def frame(self,rgb):
        self.p.stdin.write(rgb.tobytes()); self.p.stdin.flush()
        output=np.frombuffer(read_exact(self.p.stdout,rgb.size),np.uint8).reshape(rgb.shape).copy()
        field=np.fromfile(self.folder/'curves'/f'curve-{self.index:06d}.f32',dtype='<f4').reshape(3,180,320)
        self.index+=1
        return output,field

    def close(self):
        if self.p.poll() is None:
            self.p.stdin.close()
            extra=self.p.stdout.read(1)
            code=self.p.wait(timeout=30)
            self.log.close()
            if extra or code:
                raise ValueError('Replay failed or returned extra bytes')
        else:
            self.log.close()
            if self.p.returncode:
                raise ValueError('Replay exited unsuccessfully')
        log=(self.folder/'native.log').read_text()
        if 'adapter=AMD Radeon RX 7800 XT' not in log or f'completed_frames={self.index}\n' not in log:
            raise ValueError('Unexpected replay device or count')

    def terminate(self):
        if self.p.poll() is None:
            self.p.terminate(); self.p.wait(timeout=10)
        self.log.close()


def pixel_checks(source,output):
    c=source.astype(np.float32)/255
    h,w=c.shape[:2]; yy,xx=np.mgrid[:h,:w]
    u=(xx+.5)/w; v=(yy+.5)/h
    l=np.sum(c*np.array([.2126,.7152,.0722],np.float32),axis=2)
    cross=np.maximum(np.abs(u-.5)/.018,np.abs(v-.5)/.025)
    protected=(v<=.045)|(v>=.91)|(cross<=1)|(l<=.03)|(l>=.9)
    difference=np.abs(output.astype(np.int16)-source)
    return {'newly_clipped_channels':int(((((output==0)|(output==255)))&((source>0)&(source<255))).sum()),
            'new_white':int(((output==255)&(source<255)&(source>0)).sum()),
            'new_black':int(((output==0)&(source>0)&(source<255)).sum()),
            'max_rgb8_change':int(difference.max()),'protected_rgb8_max_error':int(difference[protected].max()),
            'protected_pixels':int(protected.sum())}


def main():
    out=ROOT/'runs/dce-channel-guard-v1'; old=ROOT/'runs/dce-temporal-native-v2'
    plan_path=ROOT/'scenes/playable-dce-channel-guard-v1.json'; plan=json.loads(plan_path.read_text())
    if (out/'report.json').exists():
        raise FileExistsError('Preserve the previous evaluation')
    deadline=datetime.fromisoformat(plan['deadline'])
    def time_check():
        if datetime.now(timezone.utc)>=deadline:
            raise TimeoutError('Original correction deadline reached')
    report={'schema_version':1,'status':'started','started_at':datetime.now(timezone.utc).isoformat(),'plan_sha256':digest(plan_path),'driver_sha256':digest(Path(__file__)),'fixtures':[],'control_frames':[],'frames':[]}
    shutil.copyfile(__file__,out/'driver.py')
    replay=None; decoder=None; decoder_log=None
    write_json(out/'report.json',report)
    try:
        time_check()
        active=subprocess.check_output(['powershell','-NoProfile','-Command','Get-Process -Name ArmaReforgerSteam,ArmaReforgerWorkbenchSteamDiag,enr_companion -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName; exit 0'],text=True).strip()
        if active:
            raise ValueError('A live experiment session is active')
        for name,sha in plan['source_hashes'].items():
            path=out/'original-companion.cpp' if name=='native/companion.cpp' else ROOT/name
            if digest(path)!=sha:
                raise ValueError('Changed frozen source: '+name)
        for name,sha in plan['retained_originals'].items():
            if digest(out/name)!=sha:
                raise ValueError('Changed retained original')
        old_report=json.loads((old/'report.json').read_text())
        original=(out/'original.hlsl').read_text()
        candidate=re.search(r'const char \*shader = R"\((.*?)\)";', (ROOT/'native/companion.cpp').read_text(),re.S).group(1)
        inserted=' // Keep positive common gain below a new RGB8 endpoint, including saturated colors.\n deltaGain=min(deltaGain,max(0,(254.0/255.0-maxc)/max(maxc,.001)));\n'
        if candidate.replace(inserted,'')!=original or candidate.count(inserted)!=1:
            raise ValueError('Unexpected compositor change')
        (out/'guarded.hlsl').write_text(candidate,encoding='utf-8')
        report['candidate_hashes']={name:digest(ROOT/name) for name in ['native/companion.cpp','enr/exposure_guard.py','build/Release/enr_companion.exe']}
        report['candidate_hlsl_sha256']=digest(out/'guarded.hlsl')
        weights=ROOT/'runs/pretrained/zero-dce-plusplus/weights.bin'
        cv2.setNumThreads(4); torch.set_num_threads(4)
        model_dir=weights.parent
        spec=importlib.util.spec_from_file_location('pinned_dce_guard',model_dir/'model.py')
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        model=module.enhance_net_nopool(1).eval()
        model.load_state_dict(torch.load(model_dir/'Epoch99.pth',map_location='cpu',weights_only=True),strict=True)
        snapshot=ROOT/'runs/companion-input-final-v1'
        source=np.array(Image.open(snapshot/'source.bmp').convert('RGB'))
        expected=np.array(Image.open(snapshot/'output.bmp').convert('RGB'))
        expected_curve=np.fromfile(snapshot/'curve.f32',dtype='<f4').reshape(3,180,320)
        cpu_curve=curves(source,model)
        report['independent_cpu_curve_max_error']=float(np.abs(cpu_curve-expected_curve).max())
        if report['independent_cpu_curve_max_error']>plan['gates']['cpu_curve_max_error']:
            raise ValueError('Independent CPU network mismatch')
        replay=Replay(out/'control',out/'original.hlsl',weights)
        y,r=replay.frame(source)
        if not np.array_equal(y,expected) or not np.array_equal(r,expected_curve):
            raise ValueError('Original native snapshot does not reproduce exactly')
        report['original_native_snapshot_exact']=True
        pts=np.array(json.loads((old/'source-timestamps.json').read_text()))
        retained_curves=np.load(old/'curves.npy',mmap_mode='r')
        source_path=ROOT/'runs/foliage-walk-reduced-v1/gameplay.mp4'
        command=['ffmpeg','-hide_banner','-loglevel','error','-threads','2','-i',str(source_path),'-vf','select=gte(t\\,18)*lt(t\\,28)','-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
        for phase in ['control','guarded']:
            if phase=='guarded':
                replay=Replay(out/'guarded',out/'guarded.hlsl',weights)
                residuals=np.lib.format.open_memmap(out/'residuals.npy',mode='w+',dtype=np.float32,shape=(600,252,448))
                previous=previous_residual=previous_alternating=None
                zero=np.zeros((252,448),np.float32); coeff=np.array([.2126,.7152,.0722],np.float32)
                (out/'contacts').mkdir()
                font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
            decoder_log=(out/f'{phase}-decode.log').open('wb')
            decoder=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=decoder_log)
            for index,timestamp in enumerate(pts):
                time_check(); raw=read_exact(decoder.stdout,2560*1440*3)
                rgb=np.frombuffer(raw,np.uint8).reshape(1440,2560,3)
                prior=old_report['frames'][index]
                if hashlib.sha256(raw).hexdigest()!=prior['source_rgb8_sha256']:
                    raise ValueError('Decoded source frame changed')
                start=time.perf_counter(); y,r=replay.frame(rgb); elapsed=(time.perf_counter()-start)*1000
                if not np.array_equal(r,retained_curves[index]):
                    raise ValueError('Network curves changed')
                row={'index':index,'source_pts_s':float(timestamp),'relative_pts_s':float(timestamp-pts[0]),'source_rgb8_sha256':prior['source_rgb8_sha256'],'output_rgb8_sha256':hashlib.sha256(y.tobytes()).hexdigest(),'curves_exact':True,'offline_roundtrip_ms':elapsed}
                if phase=='control':
                    if row['output_rgb8_sha256']!=prior['enhanced_rgb8_sha256']:
                        raise ValueError('Original native sequence differs')
                    row['output_exact']=True; report['control_frames'].append(row)
                else:
                    row.update(pixel_checks(rgb,y)); row['split']=prior['split']
                    residual=cv2.resize(np.sum((y.astype(np.float32)-rgb)*coeff,axis=2),(448,252),interpolation=cv2.INTER_AREA)
                    residuals[index]=residual
                    alternate=np.clip(rgb.astype(np.int16)+(8 if index%2 else -8),0,255)
                    alternate=cv2.resize(np.sum((alternate-rgb)*coeff,axis=2),(448,252),interpolation=cv2.INTER_AREA)
                    gray=cv2.cvtColor(cv2.resize(rgb,(448,252),interpolation=cv2.INTER_AREA),cv2.COLOR_RGB2GRAY)
                    if previous is not None:
                        mx,my,valid,coverage=correspondence(previous,gray,plan['parent_plan']['correspondence'])
                        if coverage!=prior['correspondence']:
                            raise ValueError('Correspondence or coverage changed')
                        row['correspondence']=coverage; row['enhancement']=metric(previous_residual,residual,mx,my,valid)
                        row['identity']=metric(zero,zero,mx,my,valid); row['alternating']=metric(previous_alternating,alternate,mx,my,valid)
                    previous=gray; previous_residual=residual; previous_alternating=alternate
                    report['frames'].append(row)
                    if index in [0,180,420,599]:
                        Image.fromarray(y).save(out/f'key-{index:04d}-guarded.png')
                    if index%60==0:
                        panel=Image.new('RGB',(1344,280),'#101820')
                        original_pair=Image.open(old/'frames'/f'{index:04d}.png')
                        panel.paste(original_pair.crop((0,32,896,536)).resize((448,252),Image.Resampling.BOX),(0,28))
                        panel.paste(original_pair.crop((896,32,1792,536)).resize((448,252),Image.Resampling.BOX),(448,28))
                        panel.paste(Image.fromarray(cv2.resize(y,(448,252),interpolation=cv2.INTER_AREA)),(896,28))
                        draw=ImageDraw.Draw(panel)
                        for x,label in [(8,'Source'),(456,'Original DCE'),(904,'Channel guard')]:
                            draw.text((x,4),f'{label} | {index/60:g}s',font=font,fill='white')
                        panel.save(out/'contacts'/f'{index:04d}.png')
                if index%60==0:
                    write_json(out/'report.json',report)
                    print(json.dumps({'phase':phase,'frame':index,'minutes_since_start':(datetime.now(timezone.utc)-datetime.fromisoformat(plan['started_at'])).total_seconds()/60,'clipped':row.get('newly_clipped_channels')}),flush=True)
            if decoder.stdout.read(1) or decoder.wait(timeout=30)!=0:
                raise ValueError('Source decoder count/exit mismatch')
            decoder=None; decoder_log.close(); decoder_log=None
            replay.close(); replay=None
            if phase=='guarded':
                residuals.flush(); del residuals
        fixture=np.array(Image.open(out/'fixture-source.png').convert('RGB'))
        sample_line='float3 r=curve.SampleLevel(linearSampler,i.uv,0).rgb;'
        for name,values in plan['fixture']['curves'].items():
            row={'name':name,'curves':values}
            expressions=[('asfloat(0x7fc00000)' if v=='nan' else 'asfloat(0x7f800000)' if v=='inf' else str(v)) for v in values]
            for variant,text in [('original',original),('guarded',candidate)]:
                time_check()
                shader=out/f'fixture-{name}-{variant}.hlsl'
                shader.write_text(text.replace(sample_line,'float3 r=float3('+','.join(expressions)+');'),encoding='utf-8')
                replay=Replay(out/f'fixture-{name}-{variant}',shader,weights)
                y,_=replay.frame(fixture); replay.close(); replay=None
                Image.fromarray(y).save(out/f'fixture-{name}-{variant}.png')
                row[variant]=pixel_checks(fixture,y)
                row[variant]['rgb8_sha256']=hashlib.sha256(y.tobytes()).hexdigest()
                row[variant]['shader_sha256']=digest(shader)
                row[variant]['png_sha256']=digest(out/f'fixture-{name}-{variant}.png')
                if variant=='guarded':
                    reference=compose_constant_curve(fixture,[float(v) for v in values])
                    error=np.abs(y.astype(np.int16)-reference)
                    row['cpu_rgb8_max_error']=int(error.max()); row['cpu_rgb8_mean_error']=float(error.mean())
                    row['source_exact']=bool(np.array_equal(y,fixture))
            report['fixtures'].append(row); write_json(out/'report.json',report)
            print(json.dumps({'fixture':name,'original':row['original']['newly_clipped_channels'],'guarded':row['guarded']['newly_clipped_channels'],'cpu_max':row['cpu_rgb8_max_error']}),flush=True)
        report['summary']=summarize(report['frames'],plan['gates']['temporal'])
        pixels=report['frames']+[r['guarded'] for r in report['fixtures']]
        report['gates']={
            'all_600_original_frames_exact':len(report['control_frames'])==600,
            'zero_newly_clipped_channels':all(r['newly_clipped_channels']==0 for r in pixels),
            'source_change_bound':all(r['max_rgb8_change']<=15 for r in pixels),
            'protected_source_identity':all(r['protected_rgb8_max_error']==0 for r in pixels),
            'fixture_cpu_max_within_one_code':all(r['cpu_rgb8_max_error']<=1 for r in report['fixtures']),
            'identity_invalid_fallback_exact':all(r['source_exact'] for r in report['fixtures'] if r['name'] not in ['bright','dark']),
            'bright_fixture_exposes_original_failure':report['fixtures'][0]['original']['newly_clipped_channels']>0,
            'coarse_temporal':all(v['controls']['enhancement']['passes_coarse_gates'] for v in report['summary'].values()),
            'sensitivity_controls':all(v['controls']['identity']['passes_coarse_gates'] and not v['controls']['alternating']['passes_coarse_gates'] for v in report['summary'].values())}
        report['all_gates_pass']=all(report['gates'].values())
        report['max_change']=max(r['max_rgb8_change'] for r in report['frames'])
        report['newly_clipped_channels']=sum(r['newly_clipped_channels'] for r in report['frames'])
        report['offline_roundtrip_ms']=stats([r['offline_roundtrip_ms'] for r in report['frames']])
        report['retained_hashes']={p.name:digest(p) for p in [out/'residuals.npy',out/'guarded.hlsl',*out.glob('key-*.png')]}
        report['status']='completed'
    except Exception:
        report['status']='failed'; report['error']=traceback.format_exc(); raise
    finally:
        if decoder is not None and decoder.poll() is None:
            decoder.terminate(); decoder.wait(timeout=10)
        if decoder_log is not None:
            decoder_log.close()
        if replay is not None:
            replay.terminate()
        report['ended_at']=datetime.now(timezone.utc).isoformat()
        report['minutes_since_original_start']=(datetime.now(timezone.utc)-datetime.fromisoformat(plan['started_at'])).total_seconds()/60
        write_json(out/'report.json',report)
        print(json.dumps({k:report.get(k) for k in ['status','all_gates_pass','gates','minutes_since_original_start']}),flush=True)


if __name__=='__main__':
    main()
