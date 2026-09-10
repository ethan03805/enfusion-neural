"""Prepare an exact isolated playable addon for Enfusion Lab compilation."""
import argparse
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import lab_modules, digest, write_json
from launch_playable import SCENES


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--lab-source', required=True)
    p.add_argument('--telemetry-hz', type=int, choices=[1,10], default=1)
    p.add_argument('--plan', type=Path, default=ROOT/'scenes/playable-sustained-v1.json')
    a = p.parse_args(); out = a.out.resolve()
    out.relative_to(ROOT / 'runs')
    if out.exists(): raise FileExistsError(out)
    initialize, _, doctor = lab_modules(a.lab_source)
    detected = doctor()
    if not detected['workbench_available']: raise ValueError('Workbench unavailable')
    initialize(out)
    # Both resolved paths are inside this new private project; preserve the scaffold.
    addon = (out / 'addon').resolve(); scaffold = (out / 'lab-scaffold').resolve()
    addon.relative_to(out); scaffold.relative_to(out)
    addon.rename(scaffold)
    shutil.copytree(ROOT / 'adapters/playable', addon)
    if a.telemetry_hz == 10:
        path = addon/'Scripts/Game/ENR_Playable.c'; text = path.read_text()
        marker = 'ENR_PlayableState.NextLog = ENR_PlayableState.Elapsed + 1;'
        if text.count(marker) != 1: raise ValueError('Unknown telemetry source')
        path.write_text(text.replace(marker,'ENR_PlayableState.NextLog = ENR_PlayableState.Elapsed + 0.1;'),encoding='utf-8')
    source = ROOT / 'adapters/enfusion/probes/ENR_SustainedMovement.c'
    shutil.copyfile(source, addon / 'Scripts/Game' / source.name)
    position, yaw, hour = SCENES['foliage-walk']
    config = 'class ENR_PlayableConfig {\n static vector Position = "%s";\n static float Yaw = %s;\n static float Hour = %s;\n static bool Automatic = false;\n}\n' % (' '.join(map(str, position)), yaw, hour)
    (addon / 'Scripts/Game/ENR_PlayableConfig.c').write_text(config, encoding='utf-8')
    shutil.copyfile(__file__, out / 'setup-driver.py')
    write_json(out / 'setup.json', {'doctor': detected,
        'plan_sha256': digest(a.plan), 'telemetry_hz': a.telemetry_hz,
        'probe_sha256': digest(source), 'driver_sha256': digest(Path(__file__)),
        'addon_hashes': {p.relative_to(addon).as_posix(): digest(p) for p in addon.rglob('*') if p.is_file()},
        'scope': 'Compilation project only; actual gameplay uses this exact addon with private settings profiles.'})
    print(out)


if __name__ == '__main__': main()
