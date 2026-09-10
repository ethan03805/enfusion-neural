"""Assemble a local Windows research package without user profiles or game assets."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    out = a.out.resolve()
    if out.exists() or out.with_suffix('.zip').exists(): raise FileExistsError(out)
    binary = ROOT/'build/Release/enr_companion.exe'
    model = ROOT/'runs/pretrained/zero-dce-plusplus'
    expected = '6d3687b8a54885adaacfb1ac1560336c6355c24237c1789d79300467773051c5'
    if sha(model/'weights.bin')!=expected: raise ValueError('Unrecognized exported checkpoint')
    out.mkdir(parents=True)
    paths = ['Start-Playable.cmd','LICENSE','scripts/play.py','scripts/launch_playable.py',
             'native/companion.cpp','native/curve_network.h','native/curve_smoke.cpp','native/enr_gpu.cpp','native/CMakeLists.txt']
    for rel in paths:
        target=out/rel; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/rel,target)
    shutil.copytree(ROOT/'adapters/playable',out/'adapters/playable')
    (out/'build/Release').mkdir(parents=True)
    shutil.copyfile(binary,out/'build/Release/enr_companion.exe')
    for name in ['weights.bin','README.md','source-pinned.json','export.json']:
        target=out/'models/zero-dce-plusplus'/name; target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(model/name,target)
    (out/'RUNME.txt').write_text('''Enfusion Neural — playable pipeline research build, 10 September 2026

This build runs a real pretrained Zero-DCE++ exposure network on the GPU over
local Arma Reforger gameplay. Its change is modest. It does not reconstruct
photorealistic materials or lighting, and it has not met the complete quality goal.

CURRENT PC: Windows, RX 7800 XT, Steam Arma Reforger, Python 3 launcher (py -3).
The companion is a standalone x64 executable with its C++ runtime linked in.
Python is used only for launching; no pip, PyTorch or CUDA is needed to play.
Close an existing Reforger session, extract this entire folder, then double-click
Start-Playable.cmd. Steam must be available. Wait for the town scene to load.

F8 = original game / resume processed overlay
F9 = identity pass / neural enhancement
F10 = quit companion, leaving the original game running
Use the normal Reforger controls. The automated path proves live movement;
physical WASD/mouse routing through the overlay still needs a user check.
If aiming or controls fail, use F8 or F10 and report the problem. A separate
viewer is available with: Start-Playable.cmd --viewer

Optional: Start-Playable.cmd --preset combined --scene town-evening
Presets: standard, scale, shadows, effects, combined.
Standard retains the source profile's texture/geometry/vegetation settings,
requests native 2560x1440 and high shadows. Combined uses 75% scale + FSR1,
medium local/low distant shadows and disables SSDO/SSR. Output stays 1440p.
Scenes: town, town-evening, foliage. Free play has no automatic walking.
Strength: --strength 0.35 (default), range 0..1.

Each launch creates runs/play-... with an isolated addon, copied settings,
game logs and companion frame timings. It does not edit Steam files or the
original user profile. Close the game normally when finished.
The launcher currently discovers the default Steam installation path and
Documents/OneDrive Documents profile. For nonstandard locations use
scripts/launch_playable.py --game ... --settings-source ... --out NEW_DIRECTORY,
then launch the native companion with the returned game PID.

Fallbacks: bypass, loss of focus, source minimization, old frames or presentation
timeout expose the source. The neural pass preserves pixel positions, limits
brightness changes, protects near-black/highlight/HUD regions and rejects invalid
curves. This is no semantic reconstruction-failure detector. Menus, scopes, rain,
interiors, HDR and multiplayer are outside the accepted coverage.

Results, normal-speed gameplay and limits:
https://ethan03805.github.io/enfusion-neural/playable.html

LICENSES: repository code MIT (LICENSE). Zero-DCE++ weights have the author's
separate academic/noncommercial research terms; see models/zero-dce-plusplus/README.md
and source-pinned.json. Author: Li et al., Learning to Enhance Low-Light Image
via Zero-Reference Deep Curve Estimation, TPAMI 2021 / Zero-DCE++.
https://github.com/Li-Chongyi/Zero-DCE_extension
No game assets, personal settings or game imagery are included in this package.
''',encoding='utf-8')
    report={'schema_version':1,'build':'playable-pipeline-2026-09-10','source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'source_scope':'Exact included source hashes identify this build, including uncommitted packaging changes at creation.',
            'model':'Zero-DCE++ Epoch99, bounded brightness-only composition','precision':'FP32','files':{str(f.relative_to(out)).replace('\\','/'):sha(f) for f in out.rglob('*') if f.is_file()}}
    (out/'manifest.json').write_text(json.dumps(report,indent=2))
    archive=out.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for f in out.rglob('*'):
            if f.is_file(): z.write(f, str(Path(out.name)/f.relative_to(out)))
    print(json.dumps({'folder':str(out),'zip':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive)},indent=2))


if __name__=='__main__': main()
