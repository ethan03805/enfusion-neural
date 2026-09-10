"""Analyze fixed-environment material candidates without registration or grading."""
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
    p.add_argument('--run', type=Path, required=True); p.add_argument('--view', choices=['closeup','approach','reverse'], required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); run = a.run.resolve(); out = a.out.resolve()
    if out.exists(): raise FileExistsError(out)
    out.mkdir(parents=True)
    plan_path = ROOT / 'scenes/playable-material-candidates-v1.json'; plan = json.loads(plan_path.read_text())
    view = next(v for v in plan['views'] if v['name'] == a.view)
    manifest = json.loads((run / 'run.json').read_text()); log = (run / 'console.log').read_text()
    if manifest['status'] != 'succeeded' or log.count('ENR_MAT_CANDIDATE completed') != 1: raise ValueError('Incomplete sequence')
    if manifest['position'] != view['position']: raise ValueError('Wrong camera position')
    paths = {name: run / 'profile/profile' / f'{name}.png' for name in ['source','candidate040','candidate070']}
    paths['restored'] = run / 'frame.png'
    arrays = {name: np.array(Image.open(path).convert('RGB'), dtype=np.float64) for name, path in paths.items()}
    if any(image.shape != (658,1199,3) for image in arrays.values()): raise ValueError('Unexpected size; do not rescale declared regions')
    if digest(paths['restored']) != manifest['image']['sha256']: raise ValueError('Lab image changed')
    phases = re.findall(r'ENR_MAT_CANDIDATE phase=(\w+) origin=(<[^>]+>) direction=(<[^>]+>) world_frame=(\d+)', log)
    expected = ['source','set040','candidate040','set070','candidate070','reset','restored']
    if [r[0] for r in phases] != expected or len({r[1:3] for r in phases}) != 1: raise ValueError('Camera or sequence changed')
    if not all(int(phases[i+1][3])>int(phases[i][3]) for i in range(6)): raise ValueError('Frames are not monotonic')
    env = re.findall(r'ENR_MAT_ENV phase=(\w+) hour=([^ ]+) wind=([^ ]+) state=([^ ]+) date=([^\r\n]+)', log)
    if [r[0] for r in env] != expected or any(r[1:] != ('13','0','Clear','1989,6,21') for r in env): raise ValueError('Environment control differs')
    exposures = re.findall(r'ENR_MAT_EXPOSURE phase=(\w+) hdr=([^ ]+) scene_middle=([^\r\n]+)', log)
    if [r[0] for r in exposures] != expected: raise ValueError('Missing exposure observation')
    hdr = [float(r[1]) for r in exposures]
    if not np.isfinite(hdr).all() or len(set(hdr)) != 1: raise ValueError('Exposure changes; do not normalize it away')
    assignments = re.findall(r'ENR_MAT_CANDIDATE cached=1 name=(.*?) index=(\d+) assigned=(\d+) value=([^\r\n]+)', log)
    if len(assignments) != 2 or any(r[0] != plan['material'] or r[2] != '1' for r in assignments) or [float(r[3]) for r in assignments] != plan['candidate_values']:
        raise ValueError('Material assignment differs')
    if any(log.count(f'ENR_MAT_CANDIDATE {name}_accepted=1') != 1 for name in ['source','candidate040','candidate070']): raise ValueError('Screenshot not accepted')
    masks = {'whole': np.ones((658,1199), dtype=bool)}
    if a.view == 'closeup':
        roof = Image.new('1',(1199,658)); ImageDraw.Draw(roof).polygon([(420,300),(805,153),(810,205),(420,330)], fill=1)
        masks['roof'] = np.asarray(roof, dtype=bool)
        masks['sky'] = np.zeros((658,1199), dtype=bool); masks['sky'][20:120,100:700] = True
    metrics = {}
    source = arrays['source']
    for name in ['candidate040','candidate070','restored']:
        output = arrays[name]; delta = np.abs(output-source)
        newly_clipped = ((source>0)&(output==0)) | ((source<255)&(output==255))
        metrics[name] = {region: {'pixels':int(mask.sum()),'mae_codes':float(delta[mask].mean()),
            'max_codes':float(delta[mask].max()),'p95_codes':float(np.percentile(delta[mask],95)),
            'newly_clipped_channel_fraction':float(newly_clipped[mask].mean()),
            'mean_rgb_codes':output[mask].mean(axis=0).tolist()} for region, mask in masks.items()}
    gates = {}
    if a.view == 'closeup':
        gates['reset_roof_mae_at_most_1'] = metrics['restored']['roof']['mae_codes']<=1
        for name in ['candidate040','candidate070']:
            gates[name+'_sky_mae_at_most_1'] = metrics[name]['sky']['mae_codes']<=1
            gates[name+'_new_roof_clipping_at_most_0001'] = metrics[name]['roof']['newly_clipped_channel_fraction']<=.001
    sources = [run/'run.json',run/'console.log',run/'addon/Scripts/Game/ENR_MaterialCandidates.c',run/'addon/Scripts/Game/ELab_GameCapture.c',
        run/'addon/Scripts/Game/ENR_ReferenceConfig.c',plan_path,Path(__file__)]+list(paths.values())
    report = {'schema_version':1,'run':run.name,'view':a.view,'split':view['split'],'phases':phases,'environment':env,'exposure':exposures,
        'assignments':assignments,'metrics':metrics,'numeric_gates':gates,'numeric_gates_pass':all(gates.values()) if gates else None,
        'images':{name:{'path':path.relative_to(ROOT).as_posix(),'sha256':digest(path)} for name,path in paths.items()},
        'source_hashes':{path.relative_to(ROOT).as_posix():digest(path) for path in sources},
        'scope':'Static native material comparison at separate simulation times; no resizing, alignment or exposure correction. Numeric gates only apply to predeclared close-up regions. Visual selection and reserved-view acceptance are separate; no neural or gameplay performance result.'}
    write_json(out/'report.json',report)
    print(json.dumps({'view':a.view,'numeric_gates':gates,'metrics':metrics},indent=2))


if __name__ == '__main__': main()
