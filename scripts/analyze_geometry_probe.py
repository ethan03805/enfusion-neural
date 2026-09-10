"""Analyze retained collision-ray logs; maps are diagnostics, not renderer buffers."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json


def vector(value):
    return [float(v) for v in value.strip('<>').split(',')]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); run = a.run.resolve(); out = a.out.resolve()
    if out.exists(): raise FileExistsError(out)
    out.mkdir(parents=True)
    manifest = json.loads((run / 'run.json').read_text())
    if manifest['status'] != 'succeeded': raise ValueError('Capture failed')
    if digest(run / 'frame.png') != manifest['image']['sha256']: raise ValueError('Image changed')
    log = (run / 'console.log').read_text()
    if log.count('ENR_GEOMETRY completed') != 1: raise ValueError('Incomplete probe')
    rows = re.findall(r'ENR_RAY mode=(\d+) index=(\d+) pixel=(<[^>]+>) start=(<[^>]+>) dir=(<[^>]+>) projected=(<[^>]+>) fraction=([^ ]+) distance=([^ ]+) normal=(<[^>]+>)', log)
    meta = re.findall(r'ENR_RAY_HIT mode=(\d+) index=(\d+) mesh=(.*?) material=(.*?) collider=([^\r\n]*)', log)
    timing = re.findall(r'ENR_GEOMETRY_TIME mode=(\d+) pass=(\d+) rays=(\d+) milliseconds=(\d+)', log)
    if len(rows) != 4608 or len(meta) != 4608 or len(timing) != 6: raise ValueError('Incomplete grid')
    modes = []; all_data = []
    for mode in range(2):
        selected = [r for r in rows if int(r[0]) == mode]
        if [int(r[1]) for r in selected] != list(range(2304)): raise ValueError('Grid index error')
        data = np.array([sum([vector(r[i]) for i in (2, 3, 4, 5)], []) + [float(r[6]), float(r[7])] + vector(r[8]) for r in selected])
        if not np.isfinite(data).all(): raise ValueError('Nonfinite values')
        hit = (data[:, 12] >= 0) & (data[:, 12] < 1)
        errors = np.linalg.norm(data[:, :2] - data[:, 9:11], axis=1)
        integer_errors = np.linalg.norm(np.floor(data[:, :2]) - data[:, 9:11], axis=1)
        normal_length = np.linalg.norm(data[:, 14:17], axis=1)
        metadata = [r for r in meta if int(r[0]) == mode]
        np.save(out / f'mode-{mode}.npy', data)
        normals = np.clip((data[:, 14:17] + 1) * 127.5, 0, 255).astype(np.uint8)
        normals[~hit] = 0
        # Nearest enlargement exposes the actual 64x36 grid; no invented detail.
        Image.fromarray(normals.reshape(36, 64, 3)).resize((1280, 720), Image.Resampling.NEAREST).save(out / f'mode-{mode}-normals.png')
        depth = np.clip(np.log1p(data[:, 12] * 250) / np.log1p(250), 0, 1)
        colors = np.stack([1 - depth, np.zeros_like(depth), depth], axis=-1)
        colors[~hit] = 0
        Image.fromarray(np.rint(colors.reshape(36, 64, 3) * 255).astype(np.uint8)).resize((1280, 720), Image.Resampling.NEAREST).save(out / f'mode-{mode}-depth.png')
        modes.append({'mode': mode, 'ray_count': 2304, 'hit_count': int(hit.sum()),
            'hit_fraction': float(hit.mean()), 'milliseconds': [int(t[3]) for t in timing if int(t[0]) == mode],
            'reprojection_error_pixels': {'max': float(errors.max()), 'median': float(np.median(errors)), 'over_half_pixel': int((errors > .5).sum()), 'passes': bool((errors <= .5).all())},
            'floor_pixel_diagnostic_error': {'max': float(integer_errors.max()), 'median': float(np.median(integer_errors))},
            'hit_normal_length': {'min': float(normal_length[hit].min()), 'max': float(normal_length[hit].max()), 'nonunit_over_001': int((np.abs(normal_length[hit] - 1) > .01).sum())},
            'hit_ray_distance_metres': {'min': float((250*data[hit, 12]).min()), 'max': float((250*data[hit, 12]).max())},
            'trace_dist': {'min': float(data[hit, 13].min()), 'max': float(data[hit, 13].max()), 'interpretation': 'Separate returned API field, not assumed equal to distance along ray'},
            'hit_meshes': dict(Counter(r[2] for r, h in zip(metadata, hit) if h)),
            'hit_materials': dict(Counter(r[3] for r, h in zip(metadata, hit) if h)),
            'arrays_sha256': digest(out / f'mode-{mode}.npy')})
        all_data.append(data)
    report = {'schema_version': 1, 'run': run.name, 'dimensions': [manifest['image']['width'], manifest['image']['height']],
        'position': manifest['position'], 'direction': manifest['direction'], 'modes': modes,
        'mode_difference': {
            'rays_with_changed_fraction': int((all_data[0][:, 12] != all_data[1][:, 12]).sum()),
            'fraction_max_abs': float(np.abs(all_data[0][:, 12] - all_data[1][:, 12]).max()),
            'normal_component_max_abs': float(np.abs(all_data[0][:, 14:17] - all_data[1][:, 14:17]).max())},
        'source_hashes': {p.relative_to(ROOT).as_posix(): digest(p) for p in [run / 'run.json', run / 'console.log', run / 'frame.png', Path(__file__)]},
        'columns': ['pixel_xyz', 'start_xyz', 'direction_xyz', 'projected_xyz', 'fraction', 'TraceDist', 'normal_xyz'],
        'scope': 'Three integer-ms Workbench samples per mode, CPU ray-grid work only. Includes allocation and metadata; excludes console emission, game frame, bridge and neural processing. RGB screenshot follows probe; no synchronized per-pixel depth/normal attachment.',
        'map_encoding': '64x36 nearest enlarged to 1280x720. Normal RGB=(world normal+1)/2; misses black. Depth red-to-blue uses log1p(ray distance)/log1p(250); misses black.'}
    write_json(out / 'report.json', report)
    print(json.dumps({k: report[k] for k in ['run', 'mode_difference']}))
    for m in modes: print(json.dumps({k: v for k, v in m.items() if k not in ['hit_meshes', 'hit_materials']}))


if __name__ == '__main__': main()
