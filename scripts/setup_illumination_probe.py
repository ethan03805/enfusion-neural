"""Initialize a bounded read-only illumination inventory in an isolated addon."""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import lab_modules, digest, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--lab-source', required=True)
    a = p.parse_args(); out = a.out.resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(out)
    plan_path = ROOT / 'scenes/playable-illumination-v1.json'
    plan = json.loads(plan_path.read_text())
    initialize, _, doctor = lab_modules(a.lab_source)
    detected = doctor()
    if not detected['workbench_available']:
        raise ValueError('Workbench unavailable')
    initialize(out)
    source = ROOT / 'adapters/enfusion/probes/ENR_IlluminationInventory.c'
    game = out / 'addon/Scripts/Game'
    shutil.copyfile(source, game / source.name)
    capture = game / 'ELab_GameCapture.c'
    script = (ROOT / 'adapters/enfusion/ELab_GameCapture.c').read_text()
    marker = '  if (ELab_CaptureState.Elapsed < ELab_CaptureState.Delay)\n   return;\n  ELab_CaptureState.Armed = false;'
    if script.count(marker) != 1:
        raise ValueError('Unexpected reference capture adapter')
    capture.write_bytes(script.replace(marker, marker.replace('  ELab_CaptureState.Armed = false;', '  if (!ENR_IlluminationInventory.Step(world, timeslice)) return;\n  ELab_CaptureState.Armed = false;')).encode())
    config = game / 'ENR_ReferenceConfig.c'
    config.write_bytes(b'#ifdef WORKBENCH\nclass ENR_ReferenceConfig { static int Year=1989; static int Month=6; static int Day=21; static float Hour=13; static float WindSpeed=0; static float WindDirection=0; static string Weather="Clear"; }\n#endif\n')
    shutil.copyfile(__file__, out / 'setup-driver.py')
    write_json(out / 'setup.json', {'doctor': detected, 'plan': plan,
        'source_hashes': {path.relative_to(ROOT).as_posix(): digest(path) for path in [source, capture, config, plan_path, Path(__file__)]}})
    print(out)


if __name__ == '__main__':
    main()
