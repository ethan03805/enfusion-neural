"""Measure the declared source/change/reset material control without image alignment."""
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
    p.add_argument('--run', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); run = a.run.resolve(); out = a.out.resolve()
    if out.exists(): raise FileExistsError(out)
    out.mkdir(parents=True)
    manifest = json.loads((run / 'run.json').read_text()); log = (run / 'console.log').read_text()
    if manifest['status'] != 'succeeded' or log.count('ENR_MAT_CONTROL completed') != 1: raise ValueError('Incomplete sequence')
    paths = {'source': run / 'profile/profile/source.png', 'changed': run / 'profile/profile/changed.png', 'restored': run / 'frame.png'}
    arrays = {name: np.array(Image.open(path).convert('RGB'), dtype=np.float64) for name, path in paths.items()}
    if any(a.shape != (658, 1199, 3) for a in arrays.values()): raise ValueError('Unexpected dimensions; do not rescale ROIs')
    if digest(paths['restored']) != manifest['image']['sha256']: raise ValueError('Lab image changed')
    phases = re.findall(r'ENR_MAT_CONTROL phase=(\w+) origin=(<[^>]+>) direction=(<[^>]+>) world_frame=(\d+)', log)
    if [r[0] for r in phases] != ['source', 'set', 'changed', 'reset', 'restored']: raise ValueError('Sequence differs')
    if len({r[1:3] for r in phases}) != 1: raise ValueError('Camera changed')
    if not all(int(phases[i+1][3]) > int(phases[i][3]) for i in range(4)): raise ValueError('Nonmonotonic frames')
    roof = Image.new('1', (1199, 658)); ImageDraw.Draw(roof).polygon([(420,300),(805,153),(810,205),(420,330)], fill=1)
    roof_mask = np.asarray(roof, dtype=bool)
    sky = np.zeros((658,1199), dtype=bool); sky[20:120,100:700] = True
    masks = {'whole': np.ones_like(sky), 'roof': roof_mask, 'sky': sky}
    metrics = {}
    for name in ['changed', 'restored']:
        delta = np.abs(arrays[name] - arrays['source'])
        metrics[name] = {region: {'pixels': int(mask.sum()), 'mae_codes': float(delta[mask].mean()),
            'max_codes': float(delta[mask].max()), 'p95_codes': float(np.percentile(delta[mask], 95)),
            'pixels_with_any_channel_over_2': int((delta.max(axis=2)[mask] > 2).sum())} for region, mask in masks.items()}
    gates = {'cached_material': 'ENR_MAT_CONTROL cached=1' in log,
        'assigned': 'index=74 assigned=1 value=0.05' in log,
        'screenshots_accepted': all(f'ENR_MAT_CONTROL {s}_accepted=1' in log for s in ['source', 'changed']),
        'visible_roof_response': metrics['changed']['roof']['mae_codes'] >= 2,
        'change_exceeds_reset_noise_5x': metrics['changed']['roof']['mae_codes'] >= 5*metrics['restored']['roof']['mae_codes'],
        'sky_stable': metrics['changed']['sky']['mae_codes'] <= 1,
        'roof_restores': metrics['restored']['roof']['mae_codes'] <= 1}
    sources = [run / 'run.json', run / 'console.log', run / 'addon/Scripts/Game/ENR_MaterialControl.c',
        run / 'addon/Scripts/Game/ELab_GameCapture.c', ROOT / 'scenes/playable-material-control-v1.json', Path(__file__)] + list(paths.values())
    report = {'schema_version': 1, 'run': run.name, 'dimensions': [1199,658], 'phases': phases,
        'api_records': [line.split('ENR_MAT_CONTROL ',1)[1] for line in log.splitlines() if 'ENR_MAT_CONTROL ' in line],
        'metrics': metrics, 'gates': gates, 'passed': all(gates.values()),
        'images': {name: {'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(path)} for name,path in paths.items()},
        'source_hashes': {path.relative_to(ROOT).as_posix(): digest(path) for path in sources},
        'scope': 'Single static Workbench sequence, byte-domain RGB differences without alignment, rescaling or exposure correction. Source/change/reset images at separate simulation times. Not full-frame exact restoration, a calibrated realistic target, neural output or gameplay performance.'}
    write_json(out / 'report.json', report)
    print(json.dumps({'passed': report['passed'], 'gates': gates, 'metrics': metrics}, indent=2))


if __name__ == '__main__': main()
