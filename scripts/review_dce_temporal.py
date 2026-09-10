"""Encode every paired replay frame at source speed and prepare fixed review aids."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr.references import digest,write_json


def main():
    run=ROOT/'runs/dce-temporal-native-v2'; out=ROOT/'runs/dce-temporal-review-v2'
    out.mkdir(parents=True,exist_ok=False); shutil.copyfile(__file__,out/'driver.py')
    parent=json.loads((run/'report.json').read_text())
    if parent['status']!='completed' or not parent['parity']['passes'] or len(parent['frames'])!=600:
        raise ValueError('Incomplete native diagnostic')
    for row in parent['frames']:
        path=run/'frames'/f'{row["index"]:04d}.png'
        if digest(path)!=row['comparison_png_sha256']:
            raise ValueError('Changed comparison frame')
    report={'schema_version':1,'parent_report_sha256':digest(run/'report.json'),'driver_sha256':digest(Path(__file__)),'status':'started'}
    write_json(out/'report.json',report)
    try:
        command=['ffmpeg','-hide_banner','-loglevel','warning','-f','concat','-safe','0','-i',str(run/'frames.ffconcat'),
                 '-t','10','-an','-c:v','libx264','-threads','4','-preset','fast','-crf','20','-pix_fmt','yuv420p',
                 '-colorspace','bt709','-color_primaries','bt709','-color_trc','iec61966-2-1','-fps_mode','vfr',
                 '-movflags','+faststart',str(out/'comparison.mp4')]
        with (out/'encode.log').open('wb') as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
                    'stream=width,height,time_base,duration,nb_frames:frame=best_effort_timestamp_time','-of','json',str(out/'comparison.mp4')]))
        write_json(out/'probe.json',probe)
        encoded=np.array([float(f['best_effort_timestamp_time']) for f in probe['frames']])
        original=np.array([r['relative_pts_s'] for r in parent['frames']])
        if len(encoded)!=len(original):
            raise ValueError('Encoded frame count differs')
        error=np.abs(encoded-original)
        report['timestamp_check']={'frames':len(encoded),'max_error_seconds':float(error.max()),'monotonic':bool(np.all(np.diff(encoded)>0)),
            'passes':bool(np.all(error<=.000001) and np.all(np.diff(encoded)>0))}
        if not report['timestamp_check']['passes']:
            raise ValueError('Output does not retain every source timestamp')
        stream=probe['streams'][0]
        if [stream['width'],stream['height']]!=[1792,536] or abs(float(stream['duration'])-10)>.001:
            raise ValueError('Wrong video dimensions or duration')
        report['stream']=stream
        report['video_sha256']=digest(out/'comparison.mp4'); report['video_bytes']=(out/'comparison.mp4').stat().st_size
        report['encode_command']=[part.replace(str(ROOT),'.') for part in command]
        report['transformation']='Every source/native-replayed 2560x1440 pair is area-reduced to 896x504 per panel with 32px labels. 600 frames over ten seconds at the original relative source PTS; no motion synthesis, speed change or audio. H264 CRF20 YUV420p alters pixels. Offline native replay, not a new gameplay performance capture.'
        sheet=Image.new('RGB',(1792,1450),'#101820'); draw=ImageDraw.Draw(sheet)
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
        for cell,index in enumerate(range(0,600,60)):
            small=Image.open(run/'frames'/f'{index:04d}.png').resize((896,268),Image.Resampling.BOX)
            x=cell%2*896; y=cell//2*290
            sheet.paste(small,(x,y+22)); draw.text((x+8,y+2),f'{index/60:.0f} seconds | frame {index:03d}',font=font,fill='white')
        sheet.save(out/'contact.png')
        shutil.copyfile(run/'frames/0180.png',out/'poster.png')
        names=['contact.png','poster.png']
        report['review_images']=[{'file':n,'sha256':digest(out/n),'dimensions':list(Image.open(out/n).size)} for n in names]
        report['keys']=[{'file':f'key-{i:04d}-{kind}.png','sha256':digest(run/f'key-{i:04d}-{kind}.png'),'dimensions':[2560,1440]} for i in [0,180,420,599] for kind in ['source','enhanced']]
        report['status']='completed'
    except Exception as e:
        report['status']='failed'; report['error']=repr(e); raise
    finally:
        write_json(out/'report.json',report)
        print(json.dumps({k:report.get(k) for k in ['status','timestamp_check','video_sha256','video_bytes']}))


if __name__=='__main__':
    main()
