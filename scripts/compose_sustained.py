"""Compose all three sustained recordings without changing elapsed speed."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs',nargs=3,type=Path); p.add_argument('--out',type=Path,required=True)
    a = p.parse_args(); a.out.mkdir(parents=True,exist_ok=False)
    labels = Image.new('RGB',(2304,32),'#101820'); draw = ImageDraw.Draw(labels)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
    for i,label in enumerate(('Standard Reforger | 1x speed','Reduced render | 1x speed','Reduced + neural | 1x speed')):
        draw.text((i*768+12,4),label,fill='white',font=font)
    labels.save(a.out/'labels.png')
    command = ['ffmpeg','-hide_banner','-loglevel','warning']
    for run in a.runs: command += ['-threads','2','-i',str(run/'gameplay.mp4')]
    command += ['-i',str(a.out/'labels.png')]
    graph = ';'.join(f'[{i}:v]setpts=PTS-STARTPTS,scale=768:432:flags=lanczos[v{i}]' for i in range(3))
    graph += ';[v0][v1][v2]hstack=inputs=3:shortest=1,pad=2304:464:0:32:black[video];[video][3:v]overlay=0:0:repeatlast=1[out]'
    target = a.out/'comparison.mp4'
    command += ['-filter_complex_threads','2','-filter_complex',graph,'-map','[out]','-an','-t','184',
        '-c:v','libx264','-threads','4','-preset','fast','-crf','26','-maxrate','3500k','-bufsize','7000k',
        '-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','iec61966-2-1',
        '-fps_mode','vfr','-movflags','+faststart',str(target)]
    subprocess.run(command,check=True)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-threads','2','-ss','20','-i',str(target),'-frames:v','1',str(a.out/'poster.png')],check=True)
    probe = json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
        'frame=best_effort_timestamp_time:stream=width,height,time_base,duration,nb_frames','-of','json',str(target)]))
    pts = np.array([float(f['best_effort_timestamp_time']) for f in probe['frames']]); np.save(a.out/'timestamps.npy',pts)
    write_json(a.out/'manifest.json',{'schema_version':1,'command':command,'driver_sha256':digest(Path(__file__)),
        'sources':{(run/'gameplay.mp4').as_posix():digest(run/'gameplay.mp4') for run in a.runs},
        'output_sha256':digest(target),'bytes':target.stat().st_size,'probe':probe['streams'][0],
        'timestamp_sha256':digest(a.out/'timestamps.npy'),'frames':len(pts),'first_pts_s':float(pts[0]),'last_pts_s':float(pts[-1]),
        'nonpositive_intervals':int((np.diff(pts)<=0).sum()),'maximum_interval_s':float(np.diff(pts).max()),
        'transformation':'All 184 seconds, original elapsed speed. Each native 2560x1440 source scaled to 768x432; three panels plus 32-pixel labels. Reset timestamp origin only. Hstack holds the last available slower-source frame. No optical flow, generated frames, speed change or audio. H264 CRF26 capped at 3.5Mbps for publication size.',
        'alignment':'Independent route repeats; capture initialization, physics and head movement differ. No pixel alignment or time warping.'})
    print(json.dumps({'bytes':target.stat().st_size,'stream':probe['streams'][0]},indent=2))


if __name__ == '__main__': main()
