"""Independent CPU evaluation of the author's sRGB Image-Adaptive-3DLUT checkpoint.

Topology follows Hui Zeng et al., Image-Adaptive-3DLUT (Apache-2.0).
This implementation uses PyTorch primitives and grid_sample in place of the
author's compiled trilinear extension. Checkpoint parameters remain unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F


def classify(x, state):
    x = F.interpolate(x, size=(256,256), mode='bilinear', align_corners=False)
    for i in [1,4,7,10,13]:
        x = F.conv2d(x, state[f'model.{i}.weight'], state[f'model.{i}.bias'], stride=2, padding=1)
        x = F.leaky_relu(x, .2)
        if i<13:
            x = F.instance_norm(x, weight=state[f'model.{i+2}.weight'], bias=state[f'model.{i+2}.bias'], eps=1e-5)
    return F.conv2d(x, state['model.16.weight'], state['model.16.bias']).flatten()


def lookup(x, lut):
    # Author layout is [channel, B, G, R], with binsize 1.0001 / (33 - 1).
    grid = (x.permute(0,2,3,1)/1.0001*2-1).unsqueeze(1)
    return F.grid_sample(lut[None], grid, mode='bilinear', padding_mode='border', align_corners=True).squeeze(2)


def smoothstep(a,b,x):
    z = ((x-a)/(b-a)).clamp(0,1)
    return z*z*(3-2*z)


def bounded(x,y,strength=.65):
    l = (x*torch.tensor([.2126,.7152,.0722])[None,:,None,None]).sum(1,keepdim=True)
    h,w = x.shape[-2:]
    yy = (torch.arange(h)+.5)/h; xx = (torch.arange(w)+.5)/w
    vertical = smoothstep(.045,.10,yy)*(1-smoothstep(.84,.91,yy))
    centre = torch.maximum(abs(xx[None,:]-.5)/.018, abs(yy[:,None]-.5)/.025)
    mask = smoothstep(.025,.09,l)*(1-smoothstep(.8,.96,l))*vertical[None,None,:,None]*smoothstep(1,2,centre)[None,None]
    return (x+(y-x).clamp(-.12,.12)*strength*mask).clamp(0,1)


def save(x,path):
    a = (x[0].permute(1,2,0).clamp(0,1).numpy()*255+.5).astype(np.uint8)
    Image.fromarray(a).save(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model', type=Path, default=Path('runs/pretrained/adaptive-3dlut'))
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('images', nargs='+', type=Path)
    a = p.parse_args(); a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    state = torch.load(a.model/'classifier.pth',map_location='cpu',weights_only=True)
    bases = torch.load(a.model/'LUTs.pth',map_location='cpu',weights_only=True)
    records = []
    with torch.inference_mode():
        for index,path in enumerate(a.images):
            x = torch.from_numpy(np.array(Image.open(path).convert('RGB'),dtype=np.float32)/255).permute(2,0,1)[None]
            start = time.perf_counter(); pred = classify(x,state)
            classifier_ms = (time.perf_counter()-start)*1000
            lut = sum(pred[i]*bases[str(i)]['LUT'] for i in range(3))
            start = time.perf_counter(); y = lookup(x,lut)
            lookup_ms = (time.perf_counter()-start)*1000
            safe = bounded(x,y)
            stem = f'{index:02d}-{path.parent.name}'
            save(x,a.out/(stem+'-source.png')); save(y,a.out/(stem+'-raw.png')); save(safe,a.out/(stem+'-bounded.png'))
            F.interpolate(x,size=(256,256),mode='bilinear',align_corners=False).numpy().astype('<f4').tofile(a.out/(stem+'-input.f32'))
            pred.numpy().astype('<f4').tofile(a.out/(stem+'-coefficients.f32'))
            lut.numpy().astype('<f4').tofile(a.out/(stem+'-lut.f32'))
            record = {'source':str(path),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'size':list(x.shape[-2:][::-1]),'coefficients':pred.tolist(),'cpu_classifier_ms':classifier_ms,'cpu_lookup_ms':lookup_ms,'cpu_timing_scope':'One cold single-thread CPU sample; not GPU or application performance','raw_mean_rgb_delta':(y-x).mean().item(),'bounded_max_abs_delta':(safe-x).abs().max().item(),'clipped_raw_fraction':((y<0)|(y>1)).float().mean().item()}
            records.append(record); print(json.dumps(record),flush=True)
    (a.out/'evaluation.json').write_text(json.dumps(records,indent=2))


if __name__ == '__main__': main()
