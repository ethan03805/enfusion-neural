"""Compose three recorded paths at original elapsed speed; never synthesize motion."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs',nargs=3,type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--note',default='')
    a=p.parse_args(); a.out.mkdir(parents=True,exist_ok=False)
    labels=Image.new('RGB',(3840,40),'#101820'); draw=ImageDraw.Draw(labels)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',26)
    for i,label in enumerate(['Standard Reforger | 1x speed','Reduced render | 1x speed','Reduced + neural | 1x speed']):
        if a.note: label+=' | '+a.note
        draw.text((i*1280+18,5),label,fill='white',font=font)
    labels.save(a.out/'labels.png')
    command=['ffmpeg','-hide_banner','-loglevel','warning']
    for run in a.runs: command+=['-threads','2','-i',str(run/'gameplay.mp4')]
    command+=['-i',str(a.out/'labels.png')]
    graph=';'.join(f'[{i}:v]setpts=PTS-STARTPTS,scale=1280:720:flags=lanczos[v{i}]' for i in range(3))
    graph+=';[v0][v1][v2]hstack=inputs=3:shortest=1,pad=3840:760:0:40:black[video];[video][3:v]overlay=0:0:repeatlast=1[out]'
    target=a.out/'comparison.mp4'
    command+=['-filter_complex_threads','2','-filter_complex',graph,'-map','[out]','-an','-t','34','-c:v','libx264','-threads','4','-preset','fast','-crf','26','-maxrate','18M','-bufsize','36M','-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','iec61966-2-1','-fps_mode','vfr','-movflags','+faststart',str(target)]
    subprocess.run(command,check=True)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-threads','2','-ss','10','-i',str(target),'-frames:v','1',str(a.out/'poster.png')],check=True)
    manifest={'schema_version':1,'command':command,'sources':{str(run/'gameplay.mp4').replace('\\','/'):hashlib.sha256((run/'gameplay.mp4').read_bytes()).hexdigest() for run in a.runs},
              'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size,'dimensions':[3840,760],
              'transformation':'Each 2560x1440 input scaled to 1280x720, three panels with 40-pixel labels. Original relative presentation timestamps retained; only timestamp origin reset. Hstack holds the last available frame of a slower input. No optical flow, generated frames, speed change or audio. Encoded H.264 CRF26, 18Mbps maximum rate.',
              'note':a.note,
              'alignment':'Separate repeat runs start recording near simulation second 28. Capture initialization and physics/head movement differ; same declared route, not frame-aligned pixels. All 34 seconds retained.'}
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest,indent=2))


if __name__=='__main__': main()
