"""Inspect a source-preserving DeepLPF transfer before spending effort on integration.

This is an offline diagnostic. It cannot add missing material information, certify
semantic visibility, or establish motion stability from still images.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def smoothstep(low, high, x):
    t = np.clip((x-low)/(high-low), 0, 1)
    return t*t*(3-2*t)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'schema_version': 1, 'status': 'started', 'input_record': 'evidence/deeplpf-evaluation-v1.json',
              'composition': {'gain_range': [.7, 1.35], 'strength': .75, 'log_gain_blur_sigma_model_pixels': 4,
                              'shadow_source_luminance_smoothstep': [.16, .4],
                              'highlight_source_luminance_reverse_smoothstep': [.85, .98],
                              'model_min_rgb_confidence_smoothstep': [.005, .04], 'max_abs_rgb_delta': .12},
              'scope': 'CPU offline diagnostic from saved model outputs. No inference, game, latency or temporal-performance claim.',
              'images': []}
    # Parameters above are fixed before viewing this diagnostic's results.
    plan = json.loads((ROOT/'scenes/playable-rgb-evaluation-v3.json').read_text())
    try:
        for i, relative in enumerate(plan['inputs']):
            src = ROOT/relative
            full = np.asarray(Image.open(src).convert('RGB'), dtype=np.float32)/255
            low = np.asarray(Image.open(ROOT/f'runs/deeplpf-evaluation-v1/{i:02d}-source-input.png'), dtype=np.float32)/255
            pred_path = ROOT/f'runs/deeplpf-evaluation-v1/{i:02d}-raw-model.npy'
            pred = np.load(pred_path)[0].transpose(1, 2, 0)
            if not np.isfinite(pred).all():
                raise ValueError('Nonfinite model output')
            confidence = smoothstep(.005, .04, pred.min(axis=2))
            loggain = np.log(np.clip((pred+.01)/(low+.01), .7, 1.35))
            loggain = gaussian_filter(loggain, sigma=(4, 4, 0))
            gain = np.stack([np.asarray(Image.fromarray(loggain[:, :, c]).resize((full.shape[1], full.shape[0]), Image.Resampling.BILINEAR)) for c in range(3)], axis=2)
            confidence = np.asarray(Image.fromarray(confidence).resize((full.shape[1], full.shape[0]), Image.Resampling.BILINEAR))
            luminance = full @ np.array([.2126, .7152, .0722], dtype=np.float32)
            weight = confidence*smoothstep(.16, .4, luminance)*(1-smoothstep(.85, .98, luminance))*.75
            # Retain a feathered fixed HUD band and crosshair. This is not HUD segmentation.
            yy, xx = np.mgrid[0:full.shape[0], 0:full.shape[1]]
            uv_y, uv_x = yy/full.shape[0], xx/full.shape[1]
            weight *= smoothstep(.04, .08, uv_y)*(1-smoothstep(.90, .96, uv_y))
            weight *= smoothstep(.008, .018, np.sqrt((uv_x-.5)**2+(uv_y-.5)**2))
            output = np.clip(full+np.clip(full*(np.exp(gain)-1), -.12, .12)*weight[:, :, None], 0, 1)
            path = out/f'{i:02d}-protected.png'
            Image.fromarray(np.round(output*255).astype(np.uint8)).save(path)
            item = {'source': relative, 'source_sha256': sha(src), 'model_output_sha256': sha(pred_path),
                    'output_sha256': sha(path), 'dimensions': [full.shape[1], full.shape[0]],
                    'max_abs_rgb_change': float(abs(output-full).max()), 'mean_abs_rgb_change': float(abs(output-full).mean()),
                    'new_black_channel_fraction_float': float(((output <= 0) & (full > 0)).mean()),
                    'shadow_max_abs_change_below_luma_016': float(abs(output-full)[luminance <= .16].max()),
                    'mean_transfer_weight': float(weight.mean())}
            report['images'].append(item)
            print(json.dumps(item), flush=True)
        report['status'] = 'completed'
    except Exception as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        (out/'report.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
