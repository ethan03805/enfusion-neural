"""Apply the declared moving-route and repeatability gates to retained gameplay."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np
from analyze_playable import analyze

ROOT = Path(__file__).resolve().parents[1]


def sample(path, times):
    return np.stack([np.interp(times, [r['simulation_s'] for r in path], [r['camera'][axis] for r in path]) for axis in range(3)], axis=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', type=Path, nargs='+')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--plan', type=Path, default=ROOT/'scenes/playable-foliage-route-v2.json')
    args = parser.parse_args()
    if args.out.exists(): raise FileExistsError(args.out)
    plan_path = args.plan.resolve()
    plan = json.loads(plan_path.read_text())
    report = {'schema_version': 1, 'plan_sha256': hashlib.sha256(plan_path.read_bytes()).hexdigest(),
              'scope': 'Camera telemetry during the declared walking interval; repeatability includes head motion. No image registration or video retiming. This is not semantic visibility acceptance.',
              'runs': []}
    reference = None
    for root in args.runs:
        config = (root/'addon/Scripts/Game/ENR_PlayableConfig.c').read_text()
        position = list(map(float, re.search(r'Position\s*=\s*"([^"]+)"', config)[1].split()))
        yaw = float(re.search(r'Yaw\s*=\s*([\d.]+)', config)[1])
        if position != plan['position'] or yaw != plan['yaw_degrees']:
            raise ValueError('Run spawn differs from the declared route')
        measured = analyze(root)
        if measured['scene'] != plan['scene'] or not measured['configuration_verified']:
            raise ValueError('Wrong scene or unverified settings')
        path = measured['path']
        if min(x['simulation_s'] for x in path)>30 or max(x['simulation_s'] for x in path)<60:
            raise ValueError('Missing full route trace')
        endpoints = sample(path, [30, 50])[:, [0, 2]]
        displacement = float(np.linalg.norm(endpoints[1]-endpoints[0]))
        times = np.arange(32, 50)
        horizontal = sample(path, times)[:, [0, 2]]
        speeds = np.linalg.norm(np.diff(horizontal, axis=0), axis=1)
        positions = sample(path, np.arange(31, 60))
        if reference is None:
            if measured['preset'] != 'standard' or measured['mode'] != 'off':
                raise ValueError('First comparison run must be standard without companion')
            reference = positions
        difference = np.linalg.norm(positions-reference, axis=1)
        item = {'run': root.name, 'horizontal_displacement_m': displacement,
                'speed_m_per_s_at_one_second_samples': list(map(float, speeds)),
                'minimum_interior_speed_m_per_s': float(speeds.min()),
                'max_repeat_camera_distance_m': float(difference.max()),
                'passes_motion_gate': bool(displacement >= plan['pilot_limits']['minimum_walk_horizontal_displacement_m'] and speeds.min() >= plan['pilot_limits']['minimum_interior_horizontal_speed_m_per_second']),
                'passes_repeat_gate': bool(difference.max() <= plan['path_agreement_max_camera_distance_m']),
                'measurement': measured}
        report['runs'].append(item)
        print(json.dumps({k: v for k, v in item.items() if k != 'measurement'}), flush=True)
    report['all_motion_and_repeat_gates_pass'] = all(r['passes_motion_gate'] and r['passes_repeat_gate'] for r in report['runs'])
    args.out.write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__': main()
