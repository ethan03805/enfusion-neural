"""Start the isolated first-person scene and live neural companion."""
import argparse
from datetime import datetime
import json
import re
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scene', choices=['town','town-evening','foliage'], default='town')
    p.add_argument('--preset', choices=['standard','scale','shadows','effects','combined'], default='standard')
    p.add_argument('--strength', type=float, default=.35)
    p.add_argument('--viewer', action='store_true', help='Use a separate ordinary viewer window instead of the overlay')
    p.add_argument('--snapshot-after', type=float, default=0, help='Optional diagnostic source/output BMP after this many seconds; adds a one-time CPU readback')
    p.add_argument('--out', type=Path)
    a = p.parse_args()
    if not 0<=a.strength<=1: p.error('Strength must be 0..1')
    processes = subprocess.check_output(['tasklist','/FI','IMAGENAME eq ArmaReforgerSteam.exe','/FO','CSV','/NH'], text=True)
    if 'ArmaReforgerSteam.exe' in processes:
        raise RuntimeError('Close the running Reforger game before starting an isolated session.')
    out = (a.out or ROOT/'runs'/('play-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6])).resolve()
    model = ROOT/'models/zero-dce-plusplus/weights.bin'
    if not model.exists(): model = ROOT/'runs/pretrained/zero-dce-plusplus/weights.bin'
    companion = ROOT/'build/Release/enr_companion.exe'
    if not companion.exists() or not model.exists():
        raise RuntimeError('Companion binary or model missing; build and prepare the model first.')
    subprocess.run([sys.executable, str(ROOT/'scripts/launch_playable.py'), '--out', str(out), '--scene', a.scene, '--preset', a.preset], check=True)
    launch = json.loads((out/'launch.json').read_text())
    print('Loading local single-player. F8: bypass, F9: identity/enhancement, F10: exit companion.', flush=True)
    deadline = time.monotonic()+120
    while time.monotonic()<deadline:
        logs = list((out/'profile/logs').glob('*/script.log'))
        text = logs[-1].read_text(errors='replace') if logs else ''
        stamps = re.findall(r'ENR_LIVE simulation_s=([0-9.]+)', text)
        if 'controlled=1' in text and stamps and float(stamps[-1])>=8: break
        time.sleep(.25)
    else: raise TimeoutError('Player did not become ready; inspect retained session logs: '+str(out))
    command = [str(companion), '--pid', str(launch['pid']), '--out', str(out/'companion'), '--mode', 'neural', '--model', str(model), '--strength', str(a.strength)]
    if not a.viewer: command.append('--overlay')
    if a.snapshot_after>0: command.extend(['--snapshot-after', str(a.snapshot_after)])
    (out/'companion-command.json').write_text(json.dumps(command, indent=2))
    result = subprocess.run(command)
    print('Companion exited. The original game remains available. Session: '+str(out))
    return result.returncode


if __name__ == '__main__':
    try: sys.exit(main())
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
