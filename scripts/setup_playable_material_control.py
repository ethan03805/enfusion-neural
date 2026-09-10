"""Create an isolated source/change/reset control using the native Material API."""
import argparse
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import lab_modules, digest, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True); p.add_argument('--lab-source', required=True)
    a = p.parse_args(); out = a.out.resolve()
    if out.exists() and any(out.iterdir()): raise FileExistsError(out)
    initialize, _, doctor = lab_modules(a.lab_source)
    detected = doctor()
    if not detected['workbench_available']: raise ValueError('Workbench unavailable')
    initialize(out)
    source = ROOT / 'adapters/enfusion/probes/ENR_MaterialControl.c'
    game = out / 'addon/Scripts/Game'; shutil.copyfile(source, game / source.name)
    capture = game / 'ELab_GameCapture.c'; script = capture.read_text()
    marker = '  ELab_CaptureState.Armed = false;'
    if script.count(marker) != 1: raise ValueError('Unexpected Lab capture script')
    capture.write_bytes(script.replace(marker, '  if (!ENR_MaterialControl.Step(world, timeslice)) return;\n' + marker).encode())
    shutil.copyfile(__file__, out / 'setup-driver.py')
    write_json(out / 'setup.json', {'doctor': detected, 'probe_sha256': digest(source),
        'capture_script_sha256': digest(capture), 'plan_sha256': digest(ROOT / 'scenes/playable-material-control-v1.json'),
        'driver_sha256': digest(Path(__file__))})
    print(str(out))


if __name__ == '__main__': main()
