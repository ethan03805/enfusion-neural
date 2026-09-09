"""Inspect screenshot/UI probe evidence without equating it with a render pass."""
import json
import math
from pathlib import Path
import re

import numpy as np
from PIL import Image

from . import model,sequence
from .references import digest


def load_probe_config(path,inventory_path=None):
    """An additional world must be observed in a completed native inventory.

    This establishes resource-name provenance only. Loadability, scene framing,
    weather and actual coverage remain runtime and visual acceptance checks.
    """
    raw=json.loads(Path(path).read_text(encoding='utf-8'));world=raw['world']
    if not isinstance(world,str):raise ValueError('World resource must be a string')
    if world=='worlds/Arland/Arland.ent':return sequence.load_config(path),None
    if not re.fullmatch(r'[A-Za-z0-9_./-]+\.ent',world) or '..' in world.split('/'):
        raise ValueError('Invalid additional world resource')
    if inventory_path is None:raise ValueError('Additional world needs a completed resource inventory')
    inventory_path=Path(inventory_path).resolve();inventory=json.loads(inventory_path.read_text(encoding='utf-8'))
    if inventory.get('schema_version')!=1 or inventory['status']!='succeeded':raise ValueError('Incomplete world inventory')
    operation=inventory.get('operation')
    if operation not in (None,'resource-inventory'):raise ValueError('Unsupported inventory operation')
    inventory_key='inventory_run' if operation=='resource-inventory' else 'capture_run'
    inventory_command='resource-inventory' if operation=='resource-inventory' else 'capture'
    manifests={};runs={}
    for key,command in [(inventory_key,inventory_command),('validation_run','validate')]:
        name=inventory[key]
        if not re.fullmatch(r'[0-9]{8}T[0-9]{6}-[a-f0-9]{10}',name):raise ValueError('Invalid inventory run ID')
        p=(inventory_path.parent/'runs'/name/'run.json').resolve()
        if not p.is_relative_to(inventory_path.parent):raise ValueError('Escaping inventory run')
        r=json.loads(p.read_text())
        if r['run_id']!=name or r['command']!=command or r['status']!='succeeded':raise ValueError('Inventory run did not complete')
        manifests[key]=p;runs[key]=r
    console=manifests[inventory_key].parent/'console.log'
    if digest(console)!=inventory['console_sha256']:raise ValueError('World inventory console changed')
    if digest(manifests[inventory_key].parent/'addon/Scripts/WorkbenchGame/ENR_ResourceProbe.c')!=inventory['probe_sha256']:
        raise ValueError('World inventory probe snapshot changed')
    if operation=='resource-inventory':
        for key,hash_key in [(inventory_key,'inventory_manifest_sha256'),('validation_run','validation_manifest_sha256')]:
            if digest(manifests[key])!=inventory[hash_key]:raise ValueError('World inventory manifest changed')
        native=runs[inventory_key]
        if native.get('process_exit_code')!=0 or native.get('terminated_owned_process') is not False:
            raise ValueError('World inventory did not exit naturally')
        plugin=manifests[inventory_key].parent/'addon/Scripts/WorkbenchGame/ENR_ResourceInventoryPlugin.c'
        if digest(plugin)!=inventory['plugin_sha256']:raise ValueError('World inventory plugin snapshot changed')
        trace=console.read_text(errors='replace')
        if any(trace.count('ENR_INVENTORY '+json.dumps({'event':event},separators=(',',':')))!=1 for event in ('started','completed')):
            raise ValueError('World inventory callback did not complete')
        for query in inventory['queries']:
            matches=re.findall(r'ENR_RESOURCE_DONE query='+re.escape(query)+r' count=(\d+) success=(\d+)',trace)
            if len(matches)!=1 or matches[0][1]!='1':raise ValueError('World inventory search did not complete')
    observed=[]
    for line in console.read_text(errors='replace').splitlines():
        if 'ENR_RESOURCE query=' not in line:continue
        match=re.search(r'\bresource=(?:\{[0-9A-Fa-f]{16}\})?([A-Za-z0-9_./-]+\.ent)(?=\s|$)',line)
        if match:observed.append(match[1])
    if world not in observed:raise ValueError('Requested world was not observed by the native inventory')
    binding={'world':world,'inventory_sha256':digest(inventory_path),'console_sha256':digest(console),
             inventory_key:inventory[inventory_key],'validation_run':inventory['validation_run'],
             ('inventory_manifest_sha256' if operation else 'capture_manifest_sha256'):digest(manifests[inventory_key]),
             'validation_manifest_sha256':digest(manifests['validation_run']),
             'scope':'Observed resource name; actual loading, framing, environment and coverage still require validation.'}
    return sequence.load_config(path,validated_world=world),binding


def events(console):
    records=[]
    for line in console.splitlines():
        if 'ENR_BRIDGE ' not in line:continue
        value=json.loads(line.split('ENR_BRIDGE ',1)[1])
        if not isinstance(value,dict) or 'event' not in value:raise ValueError('Malformed bridge event')
        records.append(value)
    return records


def pixels(path,dimensions,allow_opaque_rgb=False):
    with Image.open(path) as im:
        if im.format!='PNG' or (im.mode!='RGBA' and not (allow_opaque_rgb and im.mode=='RGB')) or list(im.size)!=dimensions:
            raise ValueError('Image format, channels or dimensions differ: '+path.name)
        values=np.array(im)
        if im.mode=='RGB':
            values=np.concatenate((values,np.full((*values.shape[:2],1),255,dtype=np.uint8)),axis=-1)
        return values


def difference(actual,expected):
    if actual.dtype!=np.uint8 or expected.dtype!=np.uint8 or actual.shape!=expected.shape or actual.shape[-1]!=4:
        raise ValueError('Expected matching RGBA8 arrays')
    error=actual.astype(np.int16)-expected.astype(np.int16);rgb=error[...,:3].astype(np.float64)
    return {'rgba_exact':bool(not np.any(error)), 'alpha_exact':bool(not np.any(error[...,3])),
            'rgba_max_error_8bit':int(np.abs(error).max()),'rgb_mae_8bit':float(np.abs(rgb).mean()),
            'rgb_rmse_8bit':float(np.sqrt(np.mean(rgb**2))),
            'rgb_changed_pixel_fraction':float(np.any(error[...,:3],axis=-1).mean())}


def operation(source,mode,weights=None):
    expected=source.copy()
    if mode=='invert':expected[...,:3]=255-source[...,:3]
    elif mode=='v0':
        if weights is None:raise ValueError('Model control needs checked weights')
        value=model.infer(source[...,:3].astype(np.float32)/255,weights)
        expected[...,:3]=np.floor(np.clip(value,0,1)*255+.5).astype(np.uint8)
    elif mode!='identity':raise ValueError('Unsupported operation')
    return expected


def inspect(root,model_path=None):
    root=Path(root).resolve();path=root/'bridge.json';probe=json.loads(path.read_text(encoding='utf-8'))
    if probe.get('schema_version')!=1 or probe['mode'] not in ('copy','identity','invert','v0'):
        raise ValueError('Unsupported bridge report')
    def directory(key):
        name=probe[key]
        if not re.fullmatch(r'[0-9]{8}T[0-9]{6}-[a-f0-9]{10}',name):raise ValueError('Invalid run ID')
        result=(root/'runs'/name).resolve()
        if not result.is_relative_to(root):raise ValueError('Escaping run directory')
        return result
    run_dir=directory('capture_run');validation_dir=directory('validation_run')
    for p,key in [(run_dir/'run.json','capture_manifest_sha256'),(validation_dir/'run.json','validation_manifest_sha256'),
                  (root/'capture-config.json','config_sha256'),(run_dir/'console.log','console_sha256')]:
        if digest(p)!=probe[key]:raise ValueError('Changed bridge evidence: '+key)
    run=json.loads((run_dir/'run.json').read_text());validation=json.loads((validation_dir/'run.json').read_text())
    config,binding=load_probe_config(root/'capture-config.json',probe.get('world_inventory_local_path'));dimensions=config['dimensions']
    if binding!=probe.get('world_binding'):raise ValueError('World resource evidence changed')
    if run['run_id']!=probe['capture_run'] or run['command']!='capture' or run['status']!=probe['capture_status']:
        raise ValueError('Capture identity differs')
    if validation['run_id']!=probe['validation_run'] or validation['command']!='validate' or validation['status']!='succeeded':
        raise ValueError('Missing compile validation')
    for relative,key in [('Scripts/Game/ENR_ImageBridge.c','probe_sha256'),('Scripts/Game/ENR_BridgeEntities.c','entities_script_sha256')]:
        if digest(run_dir/'addon'/relative)!=probe[key]:raise ValueError('Probe differs from actual run snapshot')
    position,direction=sequence.camera(config,0)
    if run['world']!=config['world'] or not np.allclose(run['position'],position,atol=.01,rtol=0) or not np.allclose(run['direction'],direction,atol=.01,rtol=0):
        raise ValueError('Unplanned capture environment')
    text=(run_dir/'console.log').read_text(errors='replace');trace=events(text)
    errors=[e['reason'] for e in trace if e['event']=='failure']+probe['worker_errors']
    if probe.get('capture_error'):errors.append(probe['capture_error'])
    source_interface=probe.get('source_interface','raw')
    if source_interface not in ('raw','file') or (source_interface=='file' and probe['mode']=='copy'):
        raise ValueError('Invalid source interface')
    result={'schema_version':1,'status':'analyzed','mode':probe['mode'],'source_interface':source_interface,'world':run['world'],'config':config,
            'probe_report_sha256':digest(path),'capture_manifest_sha256':probe['capture_manifest_sha256'],
            'world_binding':binding,
            'validation_manifest_sha256':probe['validation_manifest_sha256'],'console_sha256':probe['console_sha256'],
            'capture_run':probe['capture_run'],'validation_run':probe['validation_run'],'capture_status':run['status'],
            'probe_sha256':probe['probe_sha256'],'entities_script_sha256':probe['entities_script_sha256'],
            'entities_requested':probe['entities_requested'],'entity_records':[line.split('ENR_PROP ',1)[1] for line in text.splitlines() if 'ENR_PROP ' in line],
            'events':trace,'errors':errors,'images':{},'comparisons':{},
            'verification':{'pixel_exact_screenshot_ui_return':False,'scene_buffer_access':False,
                            'gpu_presentation_frame_identity':False,'hud_and_scope_stage':False,'live_neural_lighting_integration':False},
            'scope':'Probe of a frozen screenshot return through a UI image widget; consult verification for the actual outcome. Exact pixels do not establish a scene render pass, frame synchronization, gameplay throughput, or auxiliary-buffer access.'}
    def one(name):
        found=[e for e in trace if e['event']==name]
        if len(found)!=1:raise ValueError('Expected exactly one '+name+' event')
        return found[0]
    # A completed Lab screenshot can still be a failed bridge probe. Keep its
    # negative evidence and any real files; never silently promote the outer status.
    profile=run_dir/'profile/profile';arrays={}
    for name in ('bridge-input','bridge-output','bridge-texture','bridge-presented'):
        p=profile/(name+'.png')
        if p.exists():
            arrays[name]=pixels(p,dimensions,allow_opaque_rgb=source_interface=='file' and name=='bridge-input')
            with Image.open(p) as source_image:decoded_mode=source_image.mode
            result['images'][name]={'sha256':digest(p),'bytes':p.stat().st_size,'dimensions':dimensions,'decoded_mode':decoded_mode}
    if errors or run['status']!='succeeded':return result
    # Read actual final camera and environment telemetry, not only launch arguments.
    native=[json.loads(line.split('ELAB ',1)[1]) for line in text.splitlines() if 'ELAB {' in line]
    cameras=[e for e in native if e['event']=='camera'];viewports=[e for e in native if e['event']=='started']
    if len(cameras)!=1 or len(viewports)!=1:raise ValueError('Missing actual camera or viewport readback')
    if not np.allclose(cameras[0]['position'],position,atol=.01,rtol=0) or not np.allclose(cameras[0]['direction'],direction,atol=.01,rtol=0):
        raise ValueError('Actual camera differs')
    if [viewports[0]['viewport_width'],viewports[0]['viewport_height']]!=dimensions:raise ValueError('Actual viewport differs')
    telemetry=sequence.events(run_dir/'console.log');settings={(e['module'],e['key']):e['value'] for e in telemetry if e['event']=='setting'}
    for module,fields in config['quality_readback'].items():
        for key,value in fields.items():
            if settings.get((module,key))!=value:raise ValueError('Engine settings readback differs')
    environment=[e for e in telemetry if e['event']=='environment']
    if len(environment)!=1 or environment[0]['date']!=config['date'] or environment[0]['weather_state']!=config['weather_state']:
        raise ValueError('Actual date or weather differs')
    for key in ('hour','wind_speed_mps','wind_direction_degrees'):
        if not math.isclose(environment[0][key],config[key],abs_tol=.01):raise ValueError('Actual environment differs')
    result.update(camera_readback=cameras[0],viewport_readback=viewports[0],environment_readback=environment[0])
    request=one('requested');presentation=one('presented');completion=one('completed')
    if request['mode']!=probe['mode'] or [request['width'],request['height']]!=dimensions:
        raise ValueError('Wrong request mode or size')
    if presentation['texture_size']!=dimensions or not np.allclose(presentation['screen_size'],dimensions,atol=.01,rtol=0):
        raise ValueError('Widget texture or screen dimensions differ')
    if presentation['visible']!=1 or presentation['raw_requested']!=1:raise ValueError('Widget unavailable or readback rejected')
    ticks=[e['tick_ms'] for e in (request,presentation,completion)]
    if any(type(t)!=int or t<0 for t in ticks) or ticks!=sorted(ticks):raise ValueError('Invalid bridge timestamps')
    if presentation['world_frame']<request['world_frame']:raise ValueError('Reversed simulation frame order')
    result['observed_request_to_completed_readback_ms']=ticks[-1]-ticks[0]
    result['timing_scope']='System.GetTickCount from screenshot request until final readback has been saved. Includes deliberate settling, file operations and UI steps; not a GPU fence, display latency measurement or sustained FPS.'
    required={'bridge-texture','bridge-presented'}
    if probe['mode']!='copy':required|={'bridge-input','bridge-output'}
    if not required<=arrays.keys():raise ValueError('Missing bridge image')
    expected_saves={'bridge-texture.png','bridge-presented.png'}
    if source_interface=='file':
        if one('source_file')['submitted']!=1:raise ValueError('Source file screenshot rejected')
    elif probe['mode']!='copy':expected_saves.add('bridge-input.png')
    saved=[e for e in trace if e['event']=='saved']
    if {e['name'] for e in saved}!=expected_saves or len(saved)!=len(expected_saves):raise ValueError('Missing or duplicated raw export')
    for e in saved:
        if e['success']!=1 or [e['width'],e['height']]!=dimensions or type(e['stride'])!=int or e['stride']<dimensions[0]*4:
            raise ValueError('Invalid raw-data shape or failed save')
    if probe['mode']=='copy':
        if one('screenshot_texture')['copied']!=1 or probe['worker_records']:raise ValueError('Screenshot copy did not succeed')
        expected=arrays['bridge-texture']
    else:
        if one('file_texture')['loaded']!=1 or len(probe['worker_records'])!=1:raise ValueError('Missing CPU worker or file texture')
        worker=probe['worker_records'][0]
        if json.loads((profile/'bridge-worker.json').read_text())!=worker:raise ValueError('Worker report changed')
        for key,name in [('input_sha256','bridge-input'),('output_sha256','bridge-output')]:
            if worker[key]!=result['images'][name]['sha256']:raise ValueError('Worker image hash differs')
        if worker['status']!='succeeded' or worker['mode']!=probe['mode'] or worker['dimensions']!=dimensions or worker['worker_sha256']!=probe['worker_script_sha256']:
            raise ValueError('Worker contract differs')
        if worker.get('input_mode','RGBA')!=result['images']['bridge-input']['decoded_mode']:
            raise ValueError('Worker source channels differ')
        result['source_alpha_present']=result['images']['bridge-input']['decoded_mode']=='RGBA'
        result['input_alpha_policy']=worker.get('input_alpha_policy','preserved')
        weights=None
        if probe['mode']=='v0':
            if model_path is None or digest(model_path)!=worker['model_sha256']:raise ValueError('Missing or changed bootstrap model')
            weights=model.load(model_path)[0]
        expected=operation(arrays['bridge-input'],probe['mode'],weights)
        result['comparisons']['worker_operation']=difference(arrays['bridge-output'],expected)
        result['comparisons']['uploaded_texture']=difference(arrays['bridge-texture'],arrays['bridge-output'])
        result['external_cpu_file_pipeline_ms']=worker['external_cpu_file_pipeline_ms']
        if not math.isfinite(result['external_cpu_file_pipeline_ms']) or result['external_cpu_file_pipeline_ms']<0:raise ValueError('Invalid CPU timing')
    result['comparisons']['screen_return']=difference(arrays['bridge-presented'],expected)
    result['verification']['pixel_exact_screenshot_ui_return']=all(c['rgba_exact'] for c in result['comparisons'].values())
    return result
