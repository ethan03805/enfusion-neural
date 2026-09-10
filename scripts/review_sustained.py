"""Retain 1 Hz chronological review sheets, native keys and all video timestamps."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs', nargs='+', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--gpu-decode', action='store_true')
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=False)
    records = []
    for run in a.runs:
        video = run/'gameplay.mp4'; out = a.out/run.name; out.mkdir()
        result = json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
            'packet=pts_time:stream=width,height,avg_frame_rate,time_base,duration,nb_frames','-of','json',str(video)]))
        pts = np.sort(np.array([float(f['pts_time']) for f in result['packets']]))
        if len(pts) != int(result['streams'][0]['nb_frames']) or not np.isfinite(pts).all() or (np.diff(pts)<=0).any():
            raise ValueError('MP4 packet PTS do not establish one unique timestamp per declared frame')
        np.save(out/'timestamps.npy', pts)
        decode = ['-hwaccel','d3d11va'] if a.gpu_decode else []
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-threads','2',*decode,'-i',str(video),
            '-vf','fps=1,scale=320:180:flags=lanczos','-threads','2',str(out/'thumb-%04d.png')], check=True)
        thumbs = sorted(out.glob('thumb-*.png'))
        sheets = []
        for start in range(0,len(thumbs),48):
            selected = thumbs[start:start+48]
            canvas = Image.new('RGB',(1920,200*((len(selected)+5)//6)), '#111111')
            draw = ImageDraw.Draw(canvas)
            for i,path in enumerate(selected):
                x,y=(i%6)*320,(i//6)*200
                canvas.paste(Image.open(path).convert('RGB'),(x,y+20))
                draw.text((x+5,y+3),f'{run.name} | sample {start+i}s',fill='white')
            path = out/f'sheet-{start//48:02d}.png'; canvas.save(path)
            sheets.append({'file':path.relative_to(a.out).as_posix(),'sha256':digest(path)})
        keys = []
        for second in (3,20,41,62,83,125,167,181):
            if second > pts[-1]: continue
            path = out/f'key-{second:03d}.png'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-threads','2',*decode,'-ss',str(second),'-i',str(video),'-frames:v','1',str(path)],check=True)
            keys.append({'requested_second':second,'file':path.relative_to(a.out).as_posix(),'sha256':digest(path),
                         'dimensions':list(Image.open(path).size)})
        gaps = np.diff(pts)
        records.append({'run':run.name,'source':video.as_posix(),'source_sha256':digest(video),'stream':result['streams'][0],
            'frames':len(pts),'first_pts':float(pts[0]),'last_pts':float(pts[-1]),
            'interval_s':dict(zip(('min','p50','p95','p99','max'),map(float,np.percentile(gaps,(0,50,95,99,100))))),
            'nonpositive_intervals':int((gaps<=0).sum()),'gaps_over_50_ms':int((gaps>.05).sum()),
            'largest_gap_start_s':float(pts[int(gaps.argmax())]),'timestamp_sha256':digest(out/'timestamps.npy'),
            'sheets':sheets,'keys':keys})
    write_json(a.out/'report.json',{'schema_version':1,'driver_sha256':digest(Path(__file__)),
        'scope':'1 Hz chronological contact samples across each complete clip, plus predefined native-size keys. This is sampled visual review, not inspection of every encoded frame or continuous real-time playback. Thumbnail fps filter selects/duplicates only for contact sheets; source videos remain unchanged. Source MP4 packet PTS are sorted into presentation order and checked against declared frame count; full clips are decoded for contact extraction.',
        'gpu_decode_requested':a.gpu_decode,
        'runs':records})
    print(json.dumps([{k:v for k,v in r.items() if k not in ('sheets','keys')} for r in records],indent=2))


if __name__ == '__main__': main()
