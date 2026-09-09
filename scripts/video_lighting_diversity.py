"""Publish complete source/variant/reference paths with traceable original pixels."""
import argparse
import json
from pathlib import Path
import subprocess
from PIL import Image,ImageDraw,ImageFont
from lighting_diversity_data import sha,write


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--report',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();root=Path(a.root);report=json.loads(Path(a.report).read_text());out=Path(a.out)
    if report['status']!='succeeded' or not all(report['verification'][k] for k in ('all_display_roundtrips_within_one_code_value','all_output_alpha_exact','frozen_models','all_frames_in_declared_scope_reported')):
        raise ValueError('Unverified evaluation')
    out.mkdir(parents=True,exist_ok=False);w,h=report['plan']['dimensions'];font=ImageFont.load_default(size=16)
    result={'schema_version':1,'status':'running','report_sha256':sha(a.report),'encoder_sha256':sha(__file__),
            'selected_candidate':report['selected_candidate'],'videos':[]}
    for sequence in report['sequences']:
        frames=[c for c in report['cases'] if c['sequence']==sequence['id']]
        if [c['index'] for c in frames]!=list(range(sequence['frames'])):raise ValueError('Missing or reordered video frames')
        for variant,title in [('scene','Full scene inputs'),('relative','Without absolute position'),('rgb','RGB only')]:
            name=sequence['id']+'-'+variant;folder=out/name;folder.mkdir();records=[]
            for case in frames:
                canvas=Image.new('RGB',(w*3,h+32),(23,27,32));draw=ImageDraw.Draw(canvas)
                for i,(key,label) in enumerate([('source','Source'),(variant,title),('reference','Independent reference')]):
                    path=root/case['id']/(key+'.png')
                    if sha(path)!=case['outputs'][key]['png_sha256']:raise ValueError('Changed video input')
                    with Image.open(path) as image:
                        if image.size!=(w,h):raise ValueError('Changed video dimensions')
                        canvas.paste(image.convert('RGB'),(i*w,32))
                    draw.text((i*w+12,6),label,font=font,fill=(226,230,235))
                path=folder/f'frame-{case["index"]:04d}.png';canvas.save(path)
                records.append({'index':case['index'],'sha256':sha(path)})
            destination=out/(name+'.mp4');fps=sequence['playback_fps']
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-n','-framerate',str(fps),'-i',str(folder/'frame-%04d.png'),
                            '-frames:v',str(len(frames)),'-an','-c:v','libx264','-preset','slow','-crf','16','-pix_fmt','yuv420p','-movflags','+faststart',str(destination)],check=True,timeout=180)
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(destination)],text=True))
            if len(probe['streams'])!=1:raise ValueError('Unexpected streams')
            stream=probe['streams'][0]
            if stream['codec_name']!='h264' or [stream['width'],stream['height']]!=[w*3,h+32] or int(stream['nb_read_frames'])!=len(frames) or stream['r_frame_rate']!=str(fps)+'/1':
                raise ValueError('Wrong encoded video shape or cadence')
            result['videos'].append({'sequence':sequence['id'],'variant':variant,'file':destination.name,'sha256':sha(destination),'bytes':destination.stat().st_size,
                                     'frames':len(frames),'dimensions':[w*3,h+32],'playback_fps':fps,'duration_seconds':float(stream['duration']),
                                     'poster_frame':sequence['publication_frame'],'poster_sha256':records[sequence['publication_frame']]['sha256'],'frame_records':records,
                                     'transform':'Original 480x270 panels concatenated horizontally with 32px labels above. H.264 CRF16 yuv420p alters pixels. No scaling, interpolation, dropped frames, retiming or audio. Offline playback cadence is not inference speed.'})
            write(out/'video.json',result);print('ENR_VIDEO '+name,flush=True)
    result['status']='succeeded';write(out/'video.json',result)


if __name__=='__main__':main()
