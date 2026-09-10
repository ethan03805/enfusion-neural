"""Create the isolated, read-only geometry probe; use Enfusion Lab to validate/capture."""
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
    if out.exists() and any(out.iterdir()): raise ValueError('Use a new empty probe directory')
    initialize, _, doctor = lab_modules(a.lab_source)
    detected = doctor()
    if not detected['workbench_available']: raise ValueError('Workbench unavailable')
    initialize(out)
    source = ROOT / 'adapters/enfusion/probes/ENR_GeometryProbe.c'
    game = out / 'addon/Scripts/Game'; shutil.copyfile(source, game / source.name)
    capture = game / 'ELab_GameCapture.c'; script = capture.read_text()
    marker = '  bool accepted = System.MakeScreenshot("$profile:frame");'
    if script.count(marker) != 1: raise ValueError('Unexpected Lab capture script')
    capture.write_bytes(script.replace(marker, '  ENR_GeometryProbe.Run(world, width, height);\n' + marker).encode())
    shutil.copyfile(__file__, out / 'setup-driver.py')
    write_json(out / 'setup.json', {'doctor': detected, 'probe_sha256': digest(source),
        'capture_script_sha256': digest(capture), 'plan_sha256': digest(ROOT / 'scenes/playable-geometry-probe-v1.json'),
        'driver_sha256': digest(Path(__file__)), 'scope': 'Setup only; no geometry or performance result yet'})
    print(str(out))


if __name__ == '__main__': main()
