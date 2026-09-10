"""Measure the declared sustained route without alignment or video retiming."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json
from analyze_playable import analyze


def interpolate(path, times, key):
    return np.stack([np.interp(times, [r['simulation_s'] for r in path], [r[key][axis] for r in path]) for axis in range(3)], axis=1)


def route_metrics(path, duration, acceptance):
    times = np.arange(30, 30 + duration + 1)
    positions = interpolate(path, times, 'camera')
    horizontal = positions[:, [0, 2]]
    speeds = np.linalg.norm(np.diff(horizontal, axis=0), axis=1)
    phases = (times[:-1] - 30) % 42
    interior = ((phases >= 2) & (phases < 17)) | ((phases >= 23) & (phases < 38))
    slow = interior & (speeds < acceptance['moving_speed_m_per_s'])
    streak = longest = 0
    for value in slow:
        streak = streak + 1 if value else 0
        longest = max(longest, streak)
    moving = int((speeds >= acceptance['moving_speed_m_per_s']).sum())
    distance = float(speeds.sum())
    pilot = duration == 84
    return {'horizontal_path_length_m': distance, 'seconds_moving_at_one_second_samples': moving,
            'longest_slow_interior_seconds': longest, 'interior_speed_min_m_per_s': float(speeds[interior].min()),
            'speed_m_per_s_at_one_second_samples': speeds.tolist(),
            'passes_motion_gate': bool(moving >= acceptance['minimum_pilot_seconds_moving' if pilot else 'minimum_full_run_seconds_moving']
                and distance >= acceptance['minimum_pilot_horizontal_path_length_m' if pilot else 'minimum_full_horizontal_path_length_m']
                and longest <= acceptance['maximum_consecutive_slow_interior_seconds'])}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs', nargs='+', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--plan', type=Path, default=ROOT/'scenes/playable-sustained-v1.json')
    a = p.parse_args()
    if a.out.exists(): raise FileExistsError(a.out)
    plan = json.loads(a.plan.read_text()); report = {'schema_version': 1, 'plan': plan, 'plan_sha256': digest(a.plan), 'runs': []}
    reference = reference_direction = reference_duration = None
    for root in a.runs:
        launch = json.loads((root/'launch.json').read_text())
        if launch['sustained_plan_sha256'] != report['plan_sha256'] or launch['scene'] != plan['scene']:
            raise ValueError('Run differs from frozen plan')
        for name, sha in launch['addon_hashes'].items():
            if digest(root/'addon'/name) != sha: raise ValueError('Changed gameplay addon')
        validation = Path(launch['sustained_validation'])/'run.json'
        if digest(validation) != launch['sustained_validation_sha256']: raise ValueError('Changed validation')
        duration = launch['sustained_seconds']
        measured = analyze(root, (30,30+duration))
        if not measured['configuration_verified']: raise ValueError('Missing runtime settings')
        metrics = route_metrics(measured['path'], duration, plan['acceptance'])
        times = np.arange(31,30+duration)
        positions = interpolate(measured['path'], times, 'camera')
        direction = interpolate(measured['path'], times, 'direction')
        direction /= np.linalg.norm(direction, axis=1, keepdims=True)
        if reference is None:
            if launch['preset'] != 'standard' or launch['mode'] != 'off': raise ValueError('First pass must be standard/off')
            reference, reference_direction, reference_duration = positions, direction, duration
        if duration != reference_duration: raise ValueError('Mixed measurement durations')
        difference = np.linalg.norm(positions-reference, axis=1)
        angle = np.degrees(np.arccos(np.clip((direction*reference_direction).sum(axis=1), -1, 1)))
        metrics.update(max_repeat_camera_distance_m=float(difference.max()), max_repeat_direction_angle_degrees=float(angle.max()),
                       passes_repeat_gate=bool(difference.max() <= plan['acceptance']['maximum_cross_pass_camera_distance_m']
                           and angle.max() <= plan['acceptance']['maximum_cross_pass_direction_angle_degrees']))
        changes = launch.get('foreground_changes', [])
        start, end = measured['window']['qpc_ms']
        earlier = [x for x in changes if x['qpc_ms'] <= start]
        selected = earlier[-1:] + [x for x in changes if start < x['qpc_ms'] < end]
        metrics['foreground_observation_available'] = bool(earlier)
        metrics['foreground_changes_in_window_with_initial'] = selected
        metrics['game_foreground_through_measurement'] = bool(earlier) and all(x['pid'] == launch['pid'] for x in selected)
        row = {'run': root.name, **metrics, 'measurement': measured}
        report['runs'].append(row)
        print(json.dumps({k: v for k, v in row.items() if k not in ('measurement','speed_m_per_s_at_one_second_samples')}), flush=True)
    report['all_motion_and_repeat_gates_pass'] = all(r['passes_motion_gate'] and r['passes_repeat_gate'] for r in report['runs'])
    report['scope'] = 'Interpolated camera telemetry. Movement and repeatability gates do not establish semantic or physical-input acceptance; game/companion cadence includes recording overhead.'
    report['analysis_driver_sha256'] = digest(Path(__file__))
    report['presentation_analyzer_sha256'] = digest(ROOT/'scripts/analyze_playable.py')
    write_json(a.out, report)


if __name__ == '__main__': main()
