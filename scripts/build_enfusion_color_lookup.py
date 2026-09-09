"""Generate original lookup lattices and observe their asynchronous native build."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr import sequence
from enr.references import digest, lab_modules, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True); p.add_argument('--lab-source', required=True)
    a = p.parse_args(); out = Path(a.out).resolve()
    if out.exists() and any(out.iterdir()): raise ValueError('Choose a new empty build directory')
    plan_path = ROOT / 'scenes/color-lookup-control-v1.json'; plan = json.loads(plan_path.read_text())
    initialize, run_workbench, doctor = lab_modules(a.lab_source)
    from enfusion_lab import runner
    from enfusion_lab.config import load_project, resolve_installation
    detected = doctor()
    if not detected['workbench_available']: raise ValueError('Workbench unavailable')
    initialize(out); sequence.prepare(out, sequence.load_config(ROOT / plan['capture_base']))
    write_json(out / 'doctor.json', detected)
    relative = 'Assets/ENR_ColorLookup'; assets = out / 'addon' / relative; assets.mkdir(parents=True)
    y, x = np.indices((16, 256)); lattice = np.stack([x % 16, y, x // 16], axis=-1) * 17
    identities = []
    for case in plan['textures']:
        rgb = lattice if case == 'identity' else 255-lattice if case == 'inversion' else np.broadcast_to(plan['constant_rgb8'], lattice.shape)
        pixels = np.concatenate([rgb.astype(np.uint8), np.full((16,256,1),255,np.uint8)], axis=-1)
        name = case + '_lut'; path = assets / (name + '.tif')
        Image.fromarray(pixels).save(path, compression='tiff_lzw')
        if not np.array_equal(np.asarray(Image.open(path)), pixels): raise ValueError('Source TIFF pixels changed')
        resource = '{' + uuid.uuid4().hex[:16].upper() + '}' + relative + '/' + name + '.edds'
        metadata = ('MetaFileClass {\n Name "' + resource + '"\n Configurations {\n  TIFFResourceClass PC {\n'
                    '   SourceFile "' + path.name + '"\n   Conversion None\n   ColorSpace ToLinear\n'
                    '   GenerateMips 0\n   VolumeTexture 1\n  }\n }\n}\n')
        (assets / (name + '.edds.meta')).write_bytes(metadata.encode())
        identities.append({'case': case, 'name': name, 'source': path.name, 'source_sha256': digest(path), 'resource': resource})
    config = 'class ENR_TextureConfig { static int Count() { return 3; }\n static string Source(int index) {\n'
    for i, item in enumerate(identities): config += ' if (index == '+str(i)+') return "'+relative+'/'+item['source']+'";\n'
    config += ' return "";\n }\n}\n'
    scripts = out / 'addon/Scripts/WorkbenchGame'; (scripts / 'ENR_TextureConfig.c').write_bytes(config.encode())
    plugin = ROOT / 'adapters/enfusion/probes/ENR_TextureBuildPlugin.c'; shutil.copyfile(plugin, scripts / plugin.name)
    with sequence.private_settings(runner): validation = run_workbench(out, 'validate', timeout=180)
    if validation['status'] != 'succeeded': raise ValueError('Lookup build script did not compile')
    root, config = load_project(out); executable, game = resolve_installation(config)
    folder, record = runner.allocate_run(root, 'color-lookup-build')
    argv = [str(executable), '-gproj', str(folder / 'addon/addon.gproj'), '-addonsDir', str(game / 'addons'),
            '-profile', str(folder / 'profile'), '-cfg', str(folder / 'addon/ENR_Engine.conf'),
            '-forceSettings', str(folder / 'addon/ENR_Workbench.ini'), '-diagMenu', str(folder / 'addon/ENR_Diag.txt'),
            '-wbModule=ResourceManager', '-run', '-plugin=ENR_TextureBuildPlugin']
    record.update(argv=argv, timeout_seconds=120, scope=plan['scope']); process = None
    with runner.project_lock(root):
        folder.mkdir(parents=True); (folder / 'profile').mkdir()
        record['addon_sha256'] = runner.snapshot_addon(out / 'addon', folder / 'addon'); shutil.copyfile(__file__, folder / 'driver.py')
        record.update(status='running', started_at=runner.utc_now()); write_json(folder / 'run.json', record); start=time.monotonic()
        try:
            with (folder / 'process.log').open('wb') as log:
                startup=subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow=subprocess.SW_HIDE
                process=subprocess.Popen(argv,cwd=folder,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,shell=False,startupinfo=startup)
                record['pid']=process.pid; write_json(folder/'run.json',record); ready_at=None; previous=None
                while time.monotonic()-start < 120:
                    text=runner.collect_logs(folder/'profile')
                    paths=[folder/'addon'/relative/(v['name']+'.edds') for v in identities]
                    state=[(f.stat().st_size,f.stat().st_mtime_ns) if f.exists() else None for f in paths]
                    ready=text.count('Build successful')>=3 and 'ENR_TEXTURE queued=3' in text and all(v is not None and v[0]>148 for v in state)
                    if ready and state==previous:
                        if ready_at is None: ready_at=time.monotonic()
                        if time.monotonic()-ready_at>=10: break
                    else: ready_at=None
                    previous=state
                    if process.poll() is not None: break
                    time.sleep(.25)
                record['alive_after_build_observation']=process.poll() is None
                record['stable_output_observation_seconds']=time.monotonic()-ready_at if ready_at else None
                if not record['alive_after_build_observation'] or ready_at is None or record['stable_output_observation_seconds']<10:
                    raise ValueError('Three completed stable lookup builds were not observed')
                record['status']='succeeded'
        except (OSError,ValueError,KeyboardInterrupt) as error: record.update(status='failed',error=str(error))
        finally:
            if process is not None:
                record['terminated_owned_process']=runner.stop_owned(process); record['process_exit_code']=process.returncode
            text=runner.collect_logs(folder/'profile'); (folder/'console.log').write_bytes(text.encode())
            record.update(finished_at=runner.utc_now(),wall_seconds=time.monotonic()-start,console_sha256=digest(folder/'console.log'))
            record['retained_assets']=[{'file':f.relative_to(folder/'addon'/relative).as_posix(),'sha256':digest(f),'bytes':f.stat().st_size} for f in sorted((folder/'addon'/relative).rglob('*')) if f.is_file()]
            write_json(folder/'run.json',record)
    report={'schema_version':1,'operation':'color-lookup-build','status':record['status'],'plan':plan,'plan_sha256':digest(plan_path),
            'identities':identities,'run_id':record['run_id'],'manifest_sha256':digest(folder/'run.json'),
            'validation_run':validation['run_id'],'validation_manifest_sha256':digest(Path(validation['directory'])/'run.json'),
            'driver_sha256':digest(folder/'driver.py'),'plugin_sha256':digest(folder/'addon/Scripts/WorkbenchGame'/plugin.name),
            'console_sha256':record['console_sha256'],'retained_assets':record['retained_assets'],'rendered_response_verified':False}
    write_json(out/'build.json',report); print(json.dumps({'status':record['status'],'run':record['run_id'],'error':record.get('error')}))
    return 0 if record['status']=='succeeded' else 1


if __name__=='__main__': sys.exit(main())
