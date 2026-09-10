"""Retain original video PTS and prepare chronological review samples."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr.references import digest,write_json

def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,time_base,duration,nb_frames:frame=best_effort_timestamp_time','-of','json',str(path)]))

def main():
    run=ROOT/'runs/live-guard-v1'; out=ROOT/'runs/live-guard-review-v2'
    out.mkdir(exist_ok=False)
    shutil.copyfile(__file__,out/'driver.py')
    source=probe(run/'gameplay.mp4'); write_json(out/'source-probe.json',source)
    pts=np.array([float(f['best_effort_timestamp_time']) for f in source['frames']])
    command=['ffmpeg','-hide_banner','-loglevel','warning','-i',str(run/'gameplay.mp4'),'-vf','scale=1280:720:flags=area',
             '-an','-c:v','libx264','-threads','4','-preset','fast','-crf','22','-pix_fmt','yuv420p',
             '-colorspace','bt709','-color_primaries','bt709','-color_trc','iec61966-2-1','-fps_mode','passthrough',
             '-video_track_timescale','60000','-movflags','+faststart',str(out/'gameplay.mp4')]
    with (out/'encode.log').open('wb') as log: subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
    encoded=probe(out/'gameplay.mp4'); write_json(out/'encoded-probe.json',encoded)
    epts=np.array([float(f['best_effort_timestamp_time']) for f in encoded['frames']])
    if len(epts)!=len(pts) or np.max(np.abs(epts-pts))>0.000017: raise ValueError('Video timing changed')
    selected=[int(np.argmin(abs(pts-s))) for s in range(34)]
    keys=[selected[i] for i in [0,10,20,30]]
    sheet=Image.new('RGB',(1792,9*276),'#101820'); draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    decoder=subprocess.Popen(['ffmpeg','-v','error','-i',str(run/'gameplay.mp4'),'-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
    from scripts.evaluate_dce_temporal import read_exact
    records=[]
    for i in range(len(pts)):
        raw=read_exact(decoder.stdout,2560*1440*3)
        if i in selected:
            im=Image.frombytes('RGB',(2560,1440),raw)
            cell=selected.index(i); x=cell%4*448; y=cell//4*276
            sheet.paste(im.resize((448,252),Image.Resampling.BOX),(x,y+24))
            draw.text((x+5,y+3),f'{cell}s | frame {i}',font=font,fill='white')
            if i in keys:
                name=f'key-{cell:02d}.png'; im.save(out/name)
                records.append({'file':name,'frame':i,'pts_s':float(pts[i]),'sha256':digest(out/name)})
    if decoder.stdout.read(1) or decoder.wait(timeout=20): raise ValueError('Decode failed')
    sheet.save(out/'contact.png')
    Image.open(out/'key-10.png').resize((1280,720),Image.Resampling.BOX).save(out/'poster.png')
    report={'schema_version':1,'evaluation_sha256':digest(run/'evaluation.json'),'driver_sha256':digest(Path(__file__)),
            'source_video_sha256':digest(run/'gameplay.mp4'),'video_sha256':digest(out/'gameplay.mp4'),'video_bytes':(out/'gameplay.mp4').stat().st_size,
            'source_stream':source['streams'][0],'encoded_stream':encoded['streams'][0],
            'timestamp_check':{'frames':len(pts),'max_error_s':float(np.max(np.abs(epts-pts))),'maximum_source_gap_ms':float(np.diff(pts).max()*1000),'passes':True},
            'encode_command':command,'keys':records,'sample_count':34,
            'aids':[{ 'file':n,'sha256':digest(out/n),'dimensions':list(Image.open(out/n).size)} for n in ['contact.png','poster.png']],
            'scope':'All 34 chronological one-second samples, four full native video keys and the source/guarded native snapshot require visual review. Sampling does not establish complete 1x perceptual or visibility acceptance.',
            'transformation':'All original 2560x1440 frames area-reduced to 1280x720, H264 CRF22 YUV420p. Original relative timestamps retained within 1/60000 second; no frame synthesis, speed change or audio. Recording overhead included in live measurements.'}
    write_json(out/'report.json',report)
    print(json.dumps({'frames':len(pts),'timestamp_check':report['timestamp_check'],'video_bytes':report['video_bytes']}))

if __name__=='__main__': main()
