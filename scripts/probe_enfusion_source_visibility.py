"""Run one declared source-visibility control in a new isolated Lab project.

This captures sources only. Pixel differences do not establish correct geometry,
appearance targets, model fidelity or a renderer integration.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr import image_bridge
from enr.references import digest, write_json


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode('utf-8')).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--lab-source', required=True)
    parser.add_argument('--world-inventory', required=True)
    parser.add_argument('--scene', choices=['warehouse', 'montignac'], required=True)
    parser.add_argument('--condition', choices=['repeat', 'initial-settle', 'camera-hold'], required=True)
    args = parser.parse_args()
    plan_path = ROOT / 'scenes/arma-source-visibility-v1.json'
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    entry = plan['scenes'][args.scene]
    original, _ = image_bridge.load_probe_config(ROOT / entry['config'], args.world_inventory)
    if canonical_hash(original) != entry['canonical_config_sha256']:
        raise ValueError('Declared source configuration changed')
    config = dict(original)
    overrides = plan['conditions'][args.condition]
    if set(overrides) - {'settle_seconds', 'hold_ticks_per_sample'} or len(overrides) > 1:
        raise ValueError('Each condition must change at most one declared capture control')
    config.update(overrides)
    out = Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Use a new empty output directory')
    out.mkdir(parents=True, exist_ok=True)
    config_path = out / 'config.json'
    write_json(config_path, config)
    record = {'schema_version': 1, 'status': 'prepared', 'scene': args.scene,
              'condition': args.condition, 'overrides': overrides,
              'plan_sha256': digest(plan_path), 'driver_sha256': digest(__file__),
              'source_config_canonical_sha256': canonical_hash(original),
              'requested_config_canonical_sha256': canonical_hash(config),
              'visual_review': 'pending', 'neural_processing': False, 'aligned_reference': False}
    write_json(out / 'control.json', record)
    command = [sys.executable, str(ROOT / 'scripts/capture_enfusion_scout.py'),
               '--out', str(out / 'capture'), '--config', str(config_path),
               '--world-inventory', str(Path(args.world_inventory).resolve()),
               '--lab-source', str(Path(args.lab_source).resolve())]
    result = subprocess.run(command, cwd=ROOT, check=False)
    record['driver_exit_code'] = result.returncode
    record['status'] = 'captured' if result.returncode == 0 else 'failed'
    scout_path = out / 'capture/scout.json'
    if scout_path.exists():
        record['scout_report_sha256'] = digest(scout_path)
    write_json(out / 'control.json', record)
    if result.returncode:
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
