"""Measure the selected illumination control without alignment or normalization."""
import argparse
import json
from pathlib import Path
import re
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); run = a.run.resolve(); out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((run / 'run.json').read_text())
    log = (run / 'console.log').read_text()
    if manifest['status'] != 'succeeded' or log.count('ENR_ILLUM_CONTROL completed') != 1:
        raise ValueError('Incomplete control sequence')
    paths = {'source': run / 'profile/profile/source.png', 'changed': run / 'profile/profile/changed.png', 'restored': run / 'frame.png'}
    arrays = {name: np.array(Image.open(path).convert('RGB'), dtype=np.float64) for name, path in paths.items()}
    if any(a.shape != (658, 1199, 3) for a in arrays.values()):
        raise ValueError('Unexpected dimensions; do not resize fixed ROIs')
    if digest(paths['restored']) != manifest['image']['sha256']:
        raise ValueError('Changed Lab output')
    phases = re.findall(r'ENR_ILLUM_CONTROL phase=(\w+) origin=(<[^>]+>) direction=(<[^>]+>) world_frame=(\d+)', log)
    labels = ['source', 'set', 'changed', 'reset', 'restored']
    if [r[0] for r in phases] != labels or len({r[1:3] for r in phases}) != 1:
        raise ValueError('Changed sequence or camera')
    if any(int(phases[i+1][3]) <= int(phases[i][3]) for i in range(4)):
        raise ValueError('Nonmonotonic source frames')
    env = re.findall(r'ENR_ILLUM_ENV phase=(\w+) hour=(\S+) wind=(\S+) state=(\S+) date=(\S+)', log)
    if [r[0] for r in env] != labels or any(r[1:] != ('13', '0', 'Clear', '1989,6,21') for r in env):
        raise ValueError('Changed environment')
    exposure = re.findall(r'ENR_ILLUM_EXPOSURE phase=(\w+) hdr=(\S+) scene_middle=(\S+)', log)
    if [r[0] for r in exposure] != labels:
        raise ValueError('Missing exposure records')
    if 'index=83' not in log or 'ENR_ILLUM_CONTROL assigned=1 value=8.5' not in log:
        raise ValueError('Unexpected assignment result')
    if any(f'ENR_ILLUM_CONTROL {s}_accepted=1' not in log for s in ('source', 'changed')):
        raise ValueError('Rejected screenshot')
    roof = Image.new('1', (1199, 658))
    ImageDraw.Draw(roof).polygon([(420,300),(805,153),(810,205),(420,330)], fill=1)
    sky = np.zeros((658,1199), dtype=bool); sky[20:120,100:700] = True
    masks = {'whole': np.ones_like(sky), 'roof': np.asarray(roof, dtype=bool), 'sky': sky}
    metrics = {}
    for name in ('changed', 'restored'):
        delta = np.abs(arrays[name] - arrays['source'])
        newly_clipped = ((arrays[name] <= 0) & (arrays['source'] > 0)) | ((arrays[name] >= 255) & (arrays['source'] < 255))
        metrics[name] = {region: {'pixels': int(mask.sum()), 'mae_codes': float(delta[mask].mean()),
            'max_codes': float(delta[mask].max()), 'p95_codes': float(np.percentile(delta[mask], 95)),
            'pixels_with_any_channel_over_2': int((delta.max(axis=2)[mask] > 2).sum()),
            'newly_clipped_channel_fraction': float(newly_clipped[mask].mean())} for region, mask in masks.items()}
    sources = [run / 'run.json', run / 'console.log', run / 'addon/Scripts/Game/ENR_IlluminationControl.c',
        run / 'addon/Scripts/Game/ELab_GameCapture.c', ROOT / 'scenes/playable-illumination-v1.json',
        ROOT / 'scenes/playable-illumination-control-v1.json', Path(__file__)] + list(paths.values())
    report = {'schema_version': 1, 'status': 'completed', 'run': run.relative_to(ROOT).as_posix(),
        'dimensions': [1199,658], 'phases': phases, 'environment': env, 'exposure': exposure,
        'api_records': [line.split('ENR_ILLUM_CONTROL ',1)[1] for line in log.splitlines() if 'ENR_ILLUM_CONTROL ' in line],
        'metrics': metrics, 'numeric_controls': {
            'roof_restores': metrics['restored']['roof']['mae_codes'] <= 1,
            'roof_clipping_limit': metrics['changed']['roof']['newly_clipped_channel_fraction'] <= .001},
        'images': {name: {'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(path)} for name, path in paths.items()},
        'source_hashes': {path.relative_to(ROOT).as_posix(): digest(path) for path in sources},
        'scope': 'Static source/change/reset at separate simulation times. Raw RGB code differences; no alignment, exposure compensation or rescaling. Numeric restoration and clipping checks do not establish a visible lighting response or photorealistic improvement.'}
    write_json(out / 'report.json', report)
    print(json.dumps({'numeric_controls': report['numeric_controls'], 'metrics': metrics}, indent=2))


if __name__ == '__main__':
    main()
