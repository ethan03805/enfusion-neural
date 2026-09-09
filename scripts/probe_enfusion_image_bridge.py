"""Bounded Workbench screenshot-to-UI experiment, with optional external CPU work.

The screenshot APIs and UI widget are supported declarations. Actual success,
pixel fidelity and stage limitations must be established by each recorded run.
No native hook, game installation edit, renderer buffer or frame-time claim.
"""
import argparse
import json
from pathlib import Path
import sys
import threading
import time

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr import sequence,model
from enr.references import lab_modules,write_json,digest


def process_image(folder,mode):
    """Only a freshly created private profile is accepted by the caller."""
    start=time.perf_counter();path=folder/'bridge-input.png'
    with Image.open(path) as im:
        if im.mode!='RGBA' or im.format!='PNG':raise ValueError('Expected unconverted RGBA8 PNG')
        source=np.array(im)
    output=source.copy();weights_path=ROOT/'models/bootstrap-v0.json'
    if mode=='invert':output[...,:3]=255-source[...,:3]
    elif mode=='v0':
        weights,_=model.load(weights_path)
        rgb=model.infer(source[...,:3].astype(np.float32)/255,weights)
        output[...,:3]=np.floor(np.clip(rgb,0,1)*255+.5).astype(np.uint8)
    elif mode!='identity':raise ValueError('Unsupported file operation')
    destination=folder/'bridge-output.png'
    Image.fromarray(output).save(destination)
    report={'schema_version':1,'mode':mode,'status':'succeeded','input_sha256':digest(path),
            'output_sha256':digest(destination),'dimensions':[source.shape[1],source.shape[0]],
            'alpha_exact':bool(np.array_equal(source[...,3],output[...,3])),
            'external_cpu_file_pipeline_ms':(time.perf_counter()-start)*1000,
            'worker_sha256':digest(__file__),'model_sha256':digest(weights_path) if mode=='v0' else None,
            'scope':'Display-referred RGBA8 screenshot processing; v0 is the existing toy reference, not the scene-linear lighting model.'}
    write_json(folder/'bridge-worker.json',report)
    # The engine cannot observe a partly written image: signal only after both files close.
    (folder/'bridge-worker.done').write_text('complete\n',encoding='ascii')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--lab-source',required=True)
    p.add_argument('--mode',choices=['copy','identity','invert','v0'],required=True)
    p.add_argument('--config',default=str(ROOT/'scenes/arland-motion-v1.json'))
    p.add_argument('--entities',action='store_true',help='Spawn one observed M998 and US rifleman prefab inside this private simulation')
    a=p.parse_args();out=Path(a.out).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Use a new empty probe directory')
    initialize,run_workbench,doctor=lab_modules(a.lab_source)
    from enfusion_lab import runner
    initialize(out);c=sequence.load_config(a.config);c['samples']=1;c['position_end']=c['position_start'];c['yaw_end_degrees']=c['yaw_start_degrees']
    sequence.prepare(out,c);write_json(out/'doctor.json',doctor());write_json(out/'capture-config.json',c)
    script=ROOT/'adapters/enfusion/probes/ENR_ImageBridge.c'
    (out/'addon/Scripts/Game/ENR_ImageBridge.c').write_bytes(script.read_bytes())
    entities=ROOT/'adapters/enfusion/probes/ENR_BridgeEntities.c'
    (out/'addon/Scripts/Game/ENR_BridgeEntities.c').write_bytes(entities.read_bytes())
    (out/'addon/Scripts/Game/ENR_BridgeConfig.c').write_text('#ifdef WORKBENCH\nclass ENR_BridgeConfig { static string Mode = '+json.dumps(a.mode)+'; static bool Entities = '+str(a.entities).lower()+'; }\n#endif\n')
    capture=out/'addon/Scripts/Game/ELab_GameCapture.c';text=capture.read_text()
    needle='if (!ENR_Sequence.Tick(world, width, height)) return;'
    if text.count(needle)!=1:raise ValueError('Capture entry point changed')
    init='ENR_Sequence.Camera(world);'
    if text.count(init)!=1:raise ValueError('Camera entry point changed')
    text=text.replace(init,init+'\n  ENR_BridgeEntities.Init(world);')
    capture.write_text(text.replace(needle,'if (!ENR_ImageBridge.Tick(world, width, height)) return;'))
    stop=threading.Event();worker_records=[];worker_errors=[]
    def worker():
        try:
            while not stop.wait(.1):
                inputs=list((out/'runs').glob('*/profile/profile/bridge-input.png'))
                if len(inputs)>1:raise ValueError('More than one bridge source')
                if not inputs:continue
                path=inputs[0].resolve()
                if not path.is_relative_to(out):raise ValueError('Escaping private profile')
                # SavePixelRawData returns after writing. The file may appear earlier;
                # retry an incomplete PNG without transforming or replacing the input.
                try:
                    with Image.open(path) as image:image.verify()
                except (OSError,SyntaxError):continue
                worker_records.append(process_image(path.parent,a.mode));return
        except Exception as error:worker_errors.append(repr(error))
    with sequence.private_settings(runner):
        validation=run_workbench(out,'validate',timeout=180)
        if validation['status']!='succeeded':raise ValueError('Bridge addon did not compile')
        thread=threading.Thread(target=worker,daemon=True)
        if a.mode!='copy':thread.start()
        try:
            position,direction=sequence.camera(c,0)
            run=run_workbench(out,'capture',position=position,direction=direction,world=c['world'],settle=c['settle_seconds'],timeout=240)
        finally:
            stop.set()
            if a.mode!='copy':thread.join(timeout=30)
    directory=Path(run['directory']);lines=(directory/'console.log').read_text(errors='replace').splitlines()
    report={'schema_version':1,'mode':a.mode,'capture_status':run['status'],'validation_run':validation['run_id'],
            'capture_run':run['run_id'],'probe_sha256':digest(script),'console_sha256':digest(directory/'console.log'),
            'entities_requested':a.entities,'entities_script_sha256':digest(entities),
            'records':[s for s in lines if 'ENR_BRIDGE ' in s or 'ENR_PROP ' in s],'worker_records':worker_records,'worker_errors':worker_errors,
            'scope':'Screenshot capture and UI presentation only; no scene-buffer, HUD exclusion, GPU fence or live neural lighting integration claim.'}
    write_json(out/'bridge.json',report)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
