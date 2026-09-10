"""Run the pinned author DeepLPF checkpoint on the declared gameplay frames."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image
import torch

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    plan_path = ROOT/'scenes/playable-rgb-evaluation-v3.json'
    plan = json.loads(plan_path.read_text())
    author = ROOT/'runs/pretrained/deeplpf'
    checkpoint = author/'adobe-dpe.pt'
    if sha(checkpoint) != plan['checkpoint_sha256']:
        raise ValueError('Checkpoint hash mismatch')
    report = {'schema_version': 1, 'status': 'started', 'candidate': plan['candidate'],
              'plan_sha256': sha(plan_path), 'checkpoint_sha256': sha(checkpoint),
              'source_hashes': {f.name: sha(f) for f in author.glob('*.py')},
              'dimensions': plan['dimensions'], 'device': 'CPU', 'precision': 'FP32',
              'torch': torch.__version__, 'threads': 4,
              'preprocessing': 'Pillow bilinear resize; RGB float32 0..1; NCHW. No additional gamma or color transform.',
              'scope': 'CPU model evaluation excluding decode, resize and file writes. No GPU or application performance claim.',
              'images': []}
    try:
        # Reviewed, pinned author source stays intact and outside distributable code.
        sys.path.insert(0, str(author))
        spec = importlib.util.spec_from_file_location('deeplpf_author_model', author/'model.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        torch.set_num_threads(4)
        model = module.DeepLPFNet().eval()
        state = torch.load(checkpoint, map_location='cpu', weights_only=True)
        model.load_state_dict(state, strict=True)
        report['parameters'] = sum(p.numel() for p in model.parameters())
        with torch.inference_mode():
            for index, relative in enumerate(plan['inputs']):
                source = ROOT/relative
                im = Image.open(source).convert('RGB').resize(tuple(plan['dimensions']), Image.Resampling.BILINEAR)
                im.save(out/f'{index:02d}-source-input.png')
                x = np.ascontiguousarray((np.asarray(im, dtype=np.float32)/255).transpose(2, 0, 1)[None])
                began = time.perf_counter()
                y = model(torch.from_numpy(x)).numpy()
                elapsed = (time.perf_counter()-began)*1000
                if not np.isfinite(y).all():
                    raise ValueError('Nonfinite output')
                np.save(out/f'{index:02d}-raw-model.npy', y)
                Image.fromarray((y[0].transpose(1, 2, 0)*255).clip(0, 255).astype(np.uint8)).save(out/f'{index:02d}-raw-model.png')
                item = {'source': relative, 'source_sha256': sha(source), 'cpu_ms': elapsed,
                        'range': [float(y.min()), float(y.max())],
                        'clamped_channel_fraction': float(((y <= 0) | (y >= 1)).mean()),
                        'source_extreme_channel_fraction': float(((x <= 0) | (x >= 1)).mean()),
                        'max_abs_rgb_change': float(abs(y-x).max()), 'mean_abs_rgb_change': float(abs(y-x).mean()),
                        'raw_sha256': sha(out/f'{index:02d}-raw-model.npy')}
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
