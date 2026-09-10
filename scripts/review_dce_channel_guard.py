"""Prepare unchanged native images and explicitly scaled review aids for the guard."""
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr.references import digest,write_json


def main():
    run=ROOT/'runs/dce-channel-guard-v1'; old=ROOT/'runs/dce-temporal-native-v2'
    out=ROOT/'runs/dce-channel-guard-review-v1'; out.mkdir(exist_ok=False)
    result=json.loads((run/'report.json').read_text())
    if result['status']!='completed' or len(result['frames'])!=600 or len(result['fixtures'])!=6:
        raise ValueError('Incomplete guard evaluation')
    for name,sha in result['retained_hashes'].items():
        if digest(run/name)!=sha:
            raise ValueError('Changed retained guarded artifact')
    prior_review=json.loads((ROOT/'runs/dce-temporal-review-v2/report.json').read_text())
    for row in prior_review['keys']:
        if digest(old/row['file'])!=row['sha256']:
            raise ValueError('Original native review key changed')
    review={'schema_version':1,'measurement_sha256':digest(run/'report.json'),'driver_sha256':digest(Path(__file__)),
            'fixture_images':[],'keys':[],'aids':[],'key_differences':[]}
    for path in [run/'fixture-source.png',*sorted(run.glob('fixture-*-original.png')),*sorted(run.glob('fixture-*-guarded.png'))]:
        review['fixture_images'].append({'path':path.relative_to(ROOT).as_posix(),'sha256':digest(path),'dimensions':list(Image.open(path).size)})
    for i in [0,180,420,599]:
        source=np.array(Image.open(old/f'key-{i:04d}-source.png').convert('RGB'))
        original=np.array(Image.open(old/f'key-{i:04d}-enhanced.png').convert('RGB'))
        guarded=np.array(Image.open(run/f'key-{i:04d}-guarded.png').convert('RGB'))
        difference=np.abs(guarded.astype(np.int16)-original)
        clipped=((original==255)|(original==0))&((source>0)&(source<255))
        examples=[]
        for y,x,c in np.argwhere(clipped)[:5]:
            examples.append({'x':int(x),'y':int(y),'channel':int(c),'source_rgb8':source[y,x].tolist(),'original_rgb8':original[y,x].tolist(),'guarded_rgb8':guarded[y,x].tolist()})
        review['key_differences'].append({'frame':i,'changed_pixels':int(np.any(difference!=0,axis=2).sum()),'max_rgb8_change_from_original':int(difference.max()),'mean_rgb8_change_from_original':float(difference.mean()),'original_newly_clipped_channels':int(clipped.sum()),'first_five_original_clipping_locations':examples})
        for path in [old/f'key-{i:04d}-source.png',old/f'key-{i:04d}-enhanced.png',run/f'key-{i:04d}-guarded.png']:
            review['keys'].append({'path':path.relative_to(ROOT).as_posix(),'sha256':digest(path),'dimensions':list(Image.open(path).size)})
    contact=Image.new('RGB',(2688,1400),'#101820')
    for cell,i in enumerate(range(0,600,60)):
        panel=Image.open(run/'contacts'/f'{i:04d}.png')
        contact.paste(panel,(cell%2*1344,cell//2*280))
    contact.save(out/'contact.png')
    poster=Image.new('RGB',(2688,536),'#101820'); draw=ImageDraw.Draw(poster)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
    for x,path,label in [(0,old/'key-0420-source.png','Same source frame'),(896,old/'key-0420-enhanced.png','Original DCE | retained clipping'),(1792,run/'key-0420-guarded.png','Channel guard | offline replay')]:
        poster.paste(Image.open(path).resize((896,504),Image.Resampling.BOX),(x,32))
        draw.text((x+10,5),label,font=font,fill='white')
    poster.save(out/'poster.png')
    for path in [out/'contact.png',out/'poster.png']:
        review['aids'].append({'path':path.relative_to(ROOT).as_posix(),'sha256':digest(path),'dimensions':list(Image.open(path).size)})
    write_json(out/'report.json',review)
    print(json.dumps({'fixture_images':len(review['fixture_images']),'native_keys':len(review['keys']),'aids':len(review['aids']),'key_differences':review['key_differences']}))


if __name__=='__main__':
    main()
