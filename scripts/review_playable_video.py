"""Create local review sheets and audit elapsed-time video timestamps."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw
import numpy as np


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs',nargs='+',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=False)
    canvas=Image.new('RGB',(2560,len(a.runs)*390),'#111111'); draw=ImageDraw.Draw(canvas)
    report=[]
    for i,run in enumerate(a.runs):
        video=run/'gameplay.mp4'
        frames=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','frame=best_effort_timestamp_time','-of','json',str(video)]))['frames']
        pts=np.array([float(f['best_effort_timestamp_time']) for f in frames])
        d=np.diff(pts)
        report.append({'run':run.name,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'frames':len(pts),'first_pts_s':float(pts[0]),'last_pts_s':float(pts[-1]),'nonpositive_intervals':int((d<=0).sum()),'interval_s':dict(zip(['min','p50','p95','p99','max'],map(float,np.percentile(d,[0,50,95,99,100]))))})
        for j,second in enumerate([2,10,20,30]):
            file=a.out/f'{run.name}-{second:02d}.png'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-threads','2','-ss',str(second),'-i',str(video),'-frames:v','1',str(file)],check=True)
            im=Image.open(file).convert('RGB'); im.thumbnail((640,360))
            canvas.paste(im,(j*640,i*390+30))
            draw.text((j*640+8,i*390+8),f'{run.name} | {second}s',fill='white')
    canvas.save(a.out/'review-sheet.jpg',quality=95)
    (a.out/'timestamps.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
