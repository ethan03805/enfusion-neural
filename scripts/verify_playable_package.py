"""Bind the tested package bytes to retained launch, controls and frame evidence."""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import zipfile
from PIL import Image
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    package=ROOT/'runs/deliverables/Enfusion-Neural-Playable-2026-09-10'
    archive=package.with_suffix('.zip')
    manifest=json.loads((package/'manifest.json').read_text())
    for name,digest in manifest['files'].items():
        if sha(package/name)!=digest: raise ValueError('Package file changed: '+name)
    with zipfile.ZipFile(archive) as z:
        expected={str(Path(package.name)/name).replace('\\','/') for name in manifest['files']}|{package.name+'/manifest.json'}
        if set(z.namelist())!=expected: raise ValueError('Unlisted package contents')
        for name,digest in manifest['files'].items():
            if hashlib.sha256(z.read(package.name+'/'+name)).hexdigest()!=digest: raise ValueError('Archive differs from tested folder')
    run=package/'runs/package-launch-test-v1'
    companion=run/'companion'
    events=(companion/'events.log').read_text()
    rows=list(csv.DictReader((companion/'frames.csv').open()))
    modes=sorted({int(r['mode']) for r in rows})
    if modes!=[0,3] or 'bypass 1 ' not in events or 'bypass 0 ' not in events or 'complete frames 3770 ' not in events: raise ValueError('Controls not verified')
    source=np.array(Image.open(companion/'source.bmp').convert('RGB')).astype(np.int16)
    output=np.array(Image.open(companion/'output.bmp').convert('RGB')).astype(np.int16)
    delta=abs(source-output)
    if source.shape!=(1440,2560,3) or delta.max()>16 or not delta.any(): raise ValueError('Snapshot dimensions or bounded change failed')
    target=ROOT/'docs/downloads/playable-pipeline-2026-09-10.zip'
    target.parent.mkdir(exist_ok=True)
    if target.exists(): raise FileExistsError(target)
    shutil.copyfile(archive,target)
    report={'schema_version':1,'download_file':target.name,'sha256':sha(archive),'bytes':archive.stat().st_size,
            'package_manifest':manifest,'test':{'run':'package-launch-test-v1','status':'completed','frames':len(rows),'modes':modes,
            'controls':'Sky sent F9, F8, F8, F9, F10 to the running game. Native frames verify identity and neural modes; bypass log verifies hide/resume. Companion exits 0 while original game process remains alive. Owned game stopped only after this check.',
            'f8_handler_to_hide_ms':1.2004,'latency_scope':'Application log only; excludes key sampling and physical display',
            'physical_input':'WASD/mouse through overlay remains unverified; no user response yet',
            'snapshot':{'dimensions':[2560,1440],'max_absolute_rgb_change_8bit':int(delta.max()),'mean_absolute_rgb_change_8bit':float(delta.mean()),'changed_channel_fraction':float((delta>0).mean())},
            'native':json.loads((companion/'run.json').read_text()),'events':events,
            'hashes':{str(f.relative_to(run)).replace('\\','/'):sha(f) for f in [run/'launch.json',run/'companion-command.json',companion/'events.log',companion/'frames.csv',companion/'source.bmp',companion/'output.bmp']}}}
    (ROOT/'evidence/playable-package-v1.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'package':str(target),'sha256':report['sha256'],'test':report['test']['snapshot']},indent=2))


if __name__=='__main__': main()
