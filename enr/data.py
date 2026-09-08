"""Original procedural fixture data. No game content or downloaded weights."""
import numpy as np
from PIL import Image, ImageDraw
from .model import patches


def fixture(seed, size=128):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[:size, :size].astype(np.float32) / size
    colors = rng.uniform(0.08, 0.92, (3, 3))
    rgb = colors[0] + x[..., None]*(colors[1]-colors[0]) + y[..., None]*(colors[2]-colors[0])
    im = Image.fromarray(np.uint8(np.clip(rgb, 0, 1)*255))
    draw = ImageDraw.Draw(im)
    for _ in range(24):
        xy = rng.integers(0, size, 4).tolist()
        color = tuple(rng.integers(20, 236, 3).tolist())
        if rng.random() < .5:
            draw.line(xy, fill=color, width=int(rng.integers(1, 4)))
        else:
            a,b,c,d = xy
            draw.rectangle((min(a,c),min(b,d),max(a,c),max(b,d)), outline=color, width=2)
    return im


def degrade(image, scale=.5):
    if not 0 < scale < 1:
        raise ValueError("scale must lie strictly between 0 and 1")
    w,h = image.size
    low = image.resize((max(1, round(w*scale)), max(1, round(h*scale))), Image.Resampling.BICUBIC)
    return low.resize((w,h), Image.Resampling.BICUBIC)


def training_set(seeds, samples_per_image=2048):
    xs, ys = [], []
    for seed in seeds:
        clean = fixture(seed)
        degraded = degrade(clean)
        x = patches(np.asarray(degraded, np.float32)/255)
        y = np.asarray(clean, np.float32).reshape(-1,3)/255
        ids = np.random.default_rng(seed+20000).choice(len(x), samples_per_image, replace=False)
        xs.append(x[ids]); ys.append(y[ids])
    return np.concatenate(xs), np.concatenate(ys)
