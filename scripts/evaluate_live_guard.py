"""Evaluate the frozen live correction without changing its acceptance gates."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
import sys
import numpy as np
from PIL import Image
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr.references import digest,write_json
from analyze_playable import analyze,rows
from scripts.evaluate_dce_channel_guard import Replay,pixel_checks
from scripts.evaluate_dce_temporal import curves

def main():
    out=ROOT/'runs/live-guard-v1'
    target=out/'evaluation.json'
    if target.exists(): raise FileExistsError(target)
    plan_path=ROOT/'scenes/playable-live-guard-v1.json'
    plan=json.loads(plan_path.read_text())
    launch=json.loads((out/'launch.json').read_text())
    for name,sha in plan['processing_hashes'].items():
        if digest(ROOT/name)!=sha: raise ValueError('Frozen dependency changed: '+name)
    analysis=analyze(out)
    start,end=analysis['window']['qpc_ms']
    native=rows(out/'companion/frames.csv')
    measured=[r for r in native if start<=float(r['present_call_qpc_ms'])<end]
    events=(out/'companion/events.log').read_text()
    timed=[]
    for line in events.splitlines():
        fields=line.split()
        if fields and (fields[0] in ['hide','show','bypass'] or line.startswith('presentation wait timeout ')):
            try: at=float(fields[-1])
            except ValueError: continue
            timed.append({'event':line,'qpc_ms':at,'in_measurement':bool(start<=at<end)})
    changes=launch['foreground_changes']
    before=[x for x in changes if x['qpc_ms']<=start]
    foreground=bool(before and before[-1]['pid']==launch['pid'] and all(x['pid']==launch['pid'] for x in changes if start<x['qpc_ms']<end))
    snap=out/'companion'
    source=np.array(Image.open(snap/'source.bmp').convert('RGB'))
    output=np.array(Image.open(snap/'output.bmp').convert('RGB'))
    actual_curve=np.fromfile(snap/'curve.f32',dtype='<f4').reshape(3,180,320)
    weights=ROOT/'runs/pretrained/zero-dce-plusplus/weights.bin'
    replay=Replay(out/'snapshot-replay',ROOT/'runs/live-guard-frozen.hlsl',weights)
    try: expected,expected_curve=replay.frame(source); replay.close()
    except BaseException: replay.terminate(); raise
    torch.set_num_threads(4)
    spec=importlib.util.spec_from_file_location('live_guard_author',weights.parent/'model.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    model=module.enhance_net_nopool(1).eval()
    model.load_state_dict(torch.load(weights.parent/'Epoch99.pth',map_location='cpu',weights_only=True),strict=True)
    cpu=curves(source,model)
    numerical=pixel_checks(source,output)
    numerical.update(native_rgb8_exact=bool(np.array_equal(output,expected)),native_curve_exact=bool(np.array_equal(actual_curve,expected_curve)),independent_cpu_curve_max_error=float(np.abs(cpu-actual_curve).max()))
    for name,rgb in [('source',source),('guarded',output)]: Image.fromarray(rgb).save(out/(name+'.png'))
    post=[r for r in native if float(r['present_call_qpc_ms'])>end]
    mode_sequence=[]
    for r in post:
        mode=int(r['mode'])
        if not mode_sequence or mode_sequence[-1]!=mode: mode_sequence.append(mode)
    bypass_values=re.findall(r'^bypass ([01]) ',events,re.M)
    gates={app+'_fps':analysis[app]['mean_fps']>=30 for app in ['game','companion']}
    gates.update({app+'_p95':analysis[app]['interval_ms']['p95']<=33.3 for app in ['game','companion']})
    gates.update(foreground=foreground,no_measurement_fallback=not any(x['in_measurement'] for x in timed),
                 snapshot_rgb8_exact=numerical['native_rgb8_exact'],snapshot_curve_exact=numerical['native_curve_exact'],
                 independent_cpu_curve=numerical['independent_cpu_curve_max_error']<=.0001,
                 no_new_clipping=numerical['newly_clipped_channels']==0,protected_exact=numerical['protected_rgb8_max_error']==0,
                 bounded_change=numerical['max_rgb8_change']<=15,F8_bypass_resume=bypass_values==['1','0'],
                 F9_both_modes=mode_sequence==[3,0,3],F10_game_continues=launch['game_alive_five_seconds_after_companion_exit'])
    snapshot_frame=int(re.search(r'snapshot_readback_frame (\d+)',events)[1])
    snapshot_row=next(r for r in native if int(r['frame'])==snapshot_frame)
    gates['snapshot_outside_measurement']=float(snapshot_row['present_call_qpc_ms'])>end
    now=datetime.now(timezone.utc)
    report={'schema_version':1,'evaluated_at':now.isoformat(),'minutes_since_original_start':(now-datetime.fromisoformat(plan['started_at'])).total_seconds()/60,
            'plan_sha256':digest(plan_path),'analysis':analysis,'snapshot':numerical,'snapshot_frame':snapshot_frame,
            'snapshot_present_qpc_ms':float(snapshot_row['present_call_qpc_ms']),'control_mode_sequence':mode_sequence,'bypass_values':bypass_values,
            'events':events.splitlines(),'timed_events':timed,'foreground_changes':changes,
            'negative_capture_age_frames':[{'frame':int(r['frame']),'capture_to_present_call_ms':float(r['capture_to_present_call_ms'])} for r in measured if float(r['capture_to_present_call_ms'])<0],
            'gates':gates,'all_gates_pass':all(gates.values()),
            'scope':'Recorded moving window; recording cost included. Controls and native snapshot after measurement. Physical WASD/mouse and capture-to-display/input latency unavailable.',
            'source_hashes':{p.relative_to(ROOT).as_posix():digest(p) for p in [Path(__file__),out/'launch.json',snap/'source.bmp',snap/'output.bmp',snap/'curve.f32',out/'gameplay.mp4',out/'snapshot-replay/native.log']}}
    write_json(target,report)
    print(json.dumps({'all_gates_pass':report['all_gates_pass'],'gates':gates,'snapshot':numerical,'mode_sequence':mode_sequence,'minutes':report['minutes_since_original_start']}))

if __name__=='__main__': main()
