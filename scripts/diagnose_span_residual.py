"""Declared offline residual composition; does not alter the live companion."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json
from evaluate_span import tensor, save


def smooth(value):
    value = value.clip(0, 1)
    return value*value*(3-2*value)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    parent = ROOT / 'runs/span-evaluation-v1'; report = json.loads((parent / 'report.json').read_text())
    if report['status'] != 'completed' or not report['restoration_numeric_gate']: raise ValueError('Expected completed restoration controls')
    result = {'schema_version': 1, 'parent_report_sha256': digest(parent / 'report.json'),
        'driver_sha256': digest(Path(__file__)), 'scope': 'Offline original plus bounded SPAN-minus-bicubic residual; no new GPU/model/application measurement.',
        'parameters': {'residual_channel_bound': .06, 'strength': .5, 'dark_fade': [.05, .12],
            'highlight_fade': [.8, .9], 'HUD_unchanged': 'Top 6%, bottom 10%, left/right 4% of full image'}, 'images': []}
    write_json(out / 'parameters-before-composition.json', result)
    for i, row in enumerate(report['images']):
        source = ROOT / row['source']
        if digest(source) != row['source_sha256'] or digest(parent / f'{i:02d}-raw.npy') != row['raw_sha256']:
            raise ValueError('Input changed')
        original = Image.open(source).convert('RGB'); x = tensor(original)
        low = original.resize((1280, 720), Image.Resampling.BICUBIC)
        bicubic = tensor(low.resize(original.size, Image.Resampling.BICUBIC))
        prediction = np.load(parent / f'{i:02d}-raw.npy')
        y = x[:, 0:1]*.2126 + x[:, 1:2]*.7152 + x[:, 2:3]*.0722
        confidence = smooth((y-.05)/.07) * (1-smooth((y-.8)/.1))
        h, w = y.shape[-2:]
        confidence[:, :, :int(h*.06), :] = 0; confidence[:, :, int(h*.9):, :] = 0
        confidence[:, :, :, :int(w*.04)] = 0; confidence[:, :, :, int(w*.96):] = 0
        output = (x + .5*confidence*np.clip(prediction-bicubic, -.06, .06)).clip(0, 1)
        save(output, out / f'{i:02d}-protected.png'); np.save(out / f'{i:02d}-protected.npy', output)
        delta = np.abs(output-x)
        result['images'].append({'source': row['source'], 'source_sha256': row['source_sha256'],
            'max_abs_change': float(delta.max()), 'mean_abs_change': float(delta.mean()),
            'protected_pixels_exact': bool(np.all((delta*(confidence == 0)) == 0)),
            'new_black_channel_fraction': float(np.mean((output <= 0) & (x > 0))),
            'new_white_channel_fraction': float(np.mean((output >= 1) & (x < 1))),
            'png_sha256': digest(out / f'{i:02d}-protected.png'), 'float_sha256': digest(out / f'{i:02d}-protected.npy')})
    write_json(out / 'report.json', result)
    print(json.dumps(result['images']))


if __name__ == '__main__': main()
