"""Publish the two reviewed complete, unretimed gameplay comparisons."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    media=ROOT/'docs/media'
    manifest=json.loads((media/'manifest.json').read_text())
    evidence={'schema_version':1,'date':'2026-09-10','selection':'Complete first town and foliage/collision recorded triples, with no timing or visual selection. A separate evening run is inspected but not presented as a paired comparison.',
              'review':'Source review sheets inspect native frames at seconds 2, 10, 20 and 30. Town visibly traverses the road and turns. Foliage collides with a fence and one path differs around a tree; this limitation remains labeled. Final posters and browser playback are reviewed separately. No temporal fidelity acceptance inferred from stills.',
              'source_timestamps':json.loads((ROOT/'runs/video-review-town-v1/timestamps.json').read_text())+json.loads((ROOT/'runs/video-review-additional-v1/timestamps.json').read_text()),'outputs':[]}
    for scene in ['town','foliage']:
        run=ROOT/'runs'/('video-'+scene+'-comparison-web-v1')
        details=json.loads((run/'manifest.json').read_text())
        video=run/'comparison.mp4'
        if video.stat().st_size>=100*1024*1024 or sha(video)!=details['output_sha256']: raise ValueError('Video size/hash invalid')
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,duration,nb_frames','-show_entries','format=duration','-of','json',str(video)]))
        if abs(float(probe['format']['duration'])-34)>.04: raise ValueError('Elapsed duration changed')
        details['probe']=probe
        record='evidence/playable-video-v1.json'
        for source,name,is_video in [(video,'playable-'+scene+'-unretimed.mp4',True),(run/'poster.png','playable-'+scene+'-poster.png',False)]:
            target=media/name
            if target.exists(): raise FileExistsError(target)
            shutil.copyfile(source,target)
            entry={'file':name,'sha256':sha(target),'bytes':target.stat().st_size,'dimensions':[3840,760],'source_record':record,'source_artifact':str(source.relative_to(ROOT)).replace('\\','/'),'source_sha256':sha(source),'transformation':details['transformation'] if is_video else 'Frame at 10 seconds from the declared comparison; lossless PNG poster','rights':'Arma Reforger game imagery © Bohemia Interactive; outside MIT code license'}
            if is_video: entry.update(duration_seconds=34,playback_speed=1,retimed=False)
            else:
                with Image.open(target) as im:
                    if im.size!=(3840,760): raise ValueError('Poster size differs')
            manifest['videos' if is_video else 'images'].append(entry)
        evidence['outputs'].append(details)
    (ROOT/'evidence/playable-video-v1.json').write_text(json.dumps(evidence,indent=2))
    manifest['selection']+=' Playable gameplay: first complete town and foliage/fence-collision triples, all 34 seconds retained at original elapsed speed. Native clips retained locally.'
    (media/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Published two 34-second comparisons and two reviewed posters.')


if __name__=='__main__': main()
