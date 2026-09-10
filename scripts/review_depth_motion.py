"""Encode the retained depth sequence and verify all original relative timestamps."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr.references import digest,write_json


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();run=a.run.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    parent=json.loads((run/'report.json').read_text())
    if parent['status']!='inference_completed' or not parent['parity']['passed']:raise ValueError('Incomplete/parity-failing inference')
    if digest(run/'predictions.npy')!=parent['predictions_sha256']:raise ValueError('Changed predictions')
    report={'schema_version':1,'status':'started','parent_report_sha256':digest(run/'report.json'),'driver_sha256':digest(Path(__file__))}
    write_json(out/'report.json',report)
    try:
        target=out/'comparison.mp4'
        command=['ffmpeg','-hide_banner','-loglevel','warning','-f','concat','-safe','0','-i',str(run/'frames.ffconcat'),
            '-t','10','-an','-c:v','libx264','-threads','4','-preset','fast','-crf','20','-pix_fmt','yuv420p',
            '-colorspace','bt709','-color_primaries','bt709','-color_trc','iec61966-2-1','-fps_mode','vfr','-movflags','+faststart',str(target)]
        with (out/'encode.log').open('wb') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
        report['encode_command']=command
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
            'stream=width,height,time_base,duration,nb_frames:frame=best_effort_timestamp_time','-of','json',str(target)]))
        write_json(out/'probe.json',probe)
        output_pts=np.array([float(f['best_effort_timestamp_time']) for f in probe['frames']])
        source_pts=np.array([r['relative_pts_s'] for r in parent['frames']])
        if len(output_pts)!=len(source_pts):raise ValueError('Frame count differs after encoding')
        error=np.abs(output_pts-source_pts)
        report['timestamp_check']={'frames':len(output_pts),'maximum_error_seconds':float(error.max()),
            'strictly_increasing':bool(np.all(np.diff(output_pts)>0)),'passed':bool(np.all(error<=1/15360) and np.all(np.diff(output_pts)>0))}
        if not report['timestamp_check']['passed']:raise ValueError('Encoded timestamp check failed')
        stream=probe['streams'][0]
        if (stream['width'],stream['height'])!=(1792,536) or abs(float(stream['duration'])-10)>1/60:raise ValueError('Dimensions or duration changed')
        report['stream']=stream;report['video_sha256']=digest(target);report['video_bytes']=target.stat().st_size
        report['transformation']='Every 2560x1440 source frame area-resized to 896x504 beside its 448x252 relative depth, bilinear enlarged to 896x504 with fixed first-frame min/max and visualization-only clamp. 32px labels. H264 CRF20, YUV420p, ten seconds at original relative timestamps, verified for all 600 frames. No generated motion or audio.'
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
        sheets=[]
        for start in range(0,len(source_pts),50):
            sheet=Image.new('RGB',(2240,1440),'#101820');draw=ImageDraw.Draw(sheet)
            for j in range(start,min(start+50,len(source_pts))):
                source=run/'frames'/f'{j:04d}.png'
                if Image.open(source).size!=(1792,536):raise ValueError('Changed frame dimensions')
                small=Image.open(source).crop((0,32,1792,536)).resize((448,126),Image.Resampling.BOX)
                x=(j-start)%5*448;y=(j-start)//5*144
                sheet.paste(small,(x,y+18));draw.text((x+4,y+1),f'frame {j:03d} | {source_pts[j]:.3f}s',font=font,fill='white')
            path=out/f'contact-{start:04d}.png';sheet.save(path)
            sheets.append({'path':path.name,'sha256':digest(path),'first_frame':start,'last_frame':min(start+49,len(source_pts)-1)})
        report['contact_sheets']=sheets
        report['contact_scope']='All 600 frames in chronological source/depth thumbnails, 224x126 per panel. This is an exhaustive contact-sheet review aid, not a claim of real-time playback inspection or thin-feature acceptance.'
        report['status']='completed'
    except Exception as error:
        report.update(status='failed',error=repr(error));raise
    finally:
        write_json(out/'report.json',report);print(json.dumps(report,indent=2))


if __name__=='__main__':main()
