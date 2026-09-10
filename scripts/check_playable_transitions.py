"""One owned extracted-package session for observed menu/focus controls."""
import ctypes
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
from benchmark_playable import qpc,foreground_pid

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value): path.write_text(json.dumps(value,indent=2),encoding='utf-8')

def main():
    package=ROOT/'runs/guarded-package-audit-v1/Enfusion-Neural-Playable-2026-09-10-Guarded'
    out=ROOT/'runs/playable-transitions-v1'
    plan_path=ROOT/'scenes/playable-transitions-v1.json'
    if out.exists() or plan_path.exists(): raise FileExistsError('Retain the existing transition check')
    processes=subprocess.check_output(['tasklist','/FI','IMAGENAME eq ArmaReforgerSteam.exe','/FO','CSV','/NH'],text=True)
    if 'ArmaReforgerSteam.exe' in processes: raise RuntimeError('Existing game is not owned by this check')
    package_manifest=json.loads((package/'manifest.json').read_text())
    for rel,expected in package_manifest['files'].items():
        if sha(package/rel)!=expected: raise ValueError('Changed package: '+rel)
    spec=importlib.util.spec_from_file_location('extracted_launch',package/'scripts/launch_playable.py')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    user=Path(os.environ['USERPROFILE'])
    sources=[p for d in [user/'OneDrive/Documents',user/'Documents'] for p in (d/'My Games/ArmaReforger/profile/.save').glob('*/settings/ReforgerEngineSettings.conf')]
    if not sources: raise ValueError('No original settings profile')
    _,prepared=module.prepare(ROOT/'runs/transitions-preflight-v1','town','combined',False,sources[0])
    plan={'schema_version':1,'started_at':'2026-09-10T14:10:06+00:00','deadline':'2026-09-10T14:30:06+00:00',
          'frozen_at':datetime.now(timezone.utc).isoformat(),'package_record':'evidence/playable-package-v2.json',
          'package_sha256':sha(ROOT/'docs/downloads/playable-pipeline-2026-09-10-guarded.zip'),
          'package_manifest':package_manifest,'prepared_addon_hashes':prepared['addon_hashes'],'prepared_settings_sha256':prepared['settings_sha256'],
          'driver_sha256':sha(Path(__file__)),'scene':'town','preset':'combined','automatic':False,'strength':.35,
          'sequence':['observe live enhancement','Escape opens menu','F8 exposes original menu','click observed Resume through bypass','F8 resumes enhancement','Escape opens menu with enhancement','Escape closes menu','activate existing Steam window without input','observe game capture and native focus fallback without activating game','activate game and observe fresh-frame resumption','F10 quits companion; original game continues five seconds'],
          'neutral_window':'Existing Steam main window. Chosen before launch instead of the roadmap Codex window because Windows Computer Use excludes ChatGPT desktop UI automation. No input or screenshot of Steam content is needed.',
          'gates':['exact extracted package/addon/settings','visible menu open and close','source menu usable through bypass','overlay hides while game loses focus','new captured frames are presented after return','F10 exits successfully while game continues','no crash or presentation timeout'],
          'timing_scope':'Read-only foreground polling at 10ms and before/after UI-call wall-clock timestamps. These bound observed transitions only, not physical input or display latency. No new FPS benchmark.',
          'failure_policy':'One session, unchanged model/shader/preset. Preserve failed interactions and artifacts; do not extend the original 20-minute clock.',
          'limits':'Automated UI inputs do not establish physical WASD/mouse routing, full visibility, temporal acceptance or substantial photorealistic appearance.'}
    write(plan_path,plan)
    control=ROOT/'runs/transitions-control-v1'; control.mkdir(exist_ok=False)
    (control/'screenshots').mkdir()
    report={'schema_version':1,'plan_sha256':sha(plan_path),'created_unix_s':time.time(),'qpc_anchor_ms':qpc(),'foreground_changes':[],'status':'running'}
    launcher=None; game_handle=None
    kernel=ctypes.windll.kernel32
    kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]; kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
    kernel.TerminateProcess.argtypes=[ctypes.c_void_p,ctypes.c_uint]
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    with (control/'launcher.log').open('w',encoding='utf-8') as log:
        try:
            command=[sys.executable,str(package/'scripts/play.py'),'--out',str(out),'--scene','town','--preset','combined']
            launcher=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,cwd=package)
            report['launcher_pid']=launcher.pid; report['command']=command
            write(control/'observer.json',report)
            ready=False
            deadline=datetime.fromisoformat(plan['deadline'])
            while datetime.now(timezone.utc)<deadline:
                now=qpc(); foreground=foreground_pid()
                if not report['foreground_changes'] or report['foreground_changes'][-1]['pid']!=foreground:
                    report['foreground_changes'].append({'qpc_ms':now,'unix_s':time.time(),'pid':foreground})
                    write(control/'observer.json',report)
                if game_handle is None and (out/'launch.json').exists():
                    launch=json.loads((out/'launch.json').read_text())
                    if launch['addon_hashes']!=plan['prepared_addon_hashes'] or launch['settings_sha256']!=plan['prepared_settings_sha256']:
                        raise ValueError('Actual private addon or settings differ from preflight')
                    if str(out/'addon/addon.gproj') not in launch['argv']: raise ValueError('Unexpected owned game project')
                    game_handle=kernel.OpenProcess(0x100000|0x1,False,launch['pid'])
                    if not game_handle: raise OSError('Cannot retain owned game process handle')
                    report['game_pid']=launch['pid']; report['actual_settings_and_addon_match']=True
                if game_handle and kernel.WaitForSingleObject(game_handle,0)!=258:
                    raise RuntimeError('Owned game exited during transition checks')
                frames=out/'companion/frames.csv'
                if not ready and frames.exists() and frames.stat().st_size>1000:
                    ready=True; report['ready_qpc_ms']=qpc(); write(control/'observer.json',report)
                    print('TRANSITIONS_READY: exact extracted package is producing frames.',flush=True)
                code=launcher.poll()
                if code is not None:
                    report['launcher_exit_code']=code; report['launcher_exit_qpc_ms']=qpc()
                    if code or not ready: raise RuntimeError('Launcher failed before completed controls')
                    time.sleep(5)
                    report['game_alive_five_seconds_after_companion_exit']=kernel.WaitForSingleObject(game_handle,0)==258
                    if not report['game_alive_five_seconds_after_companion_exit']: raise RuntimeError('Game did not continue')
                    report['status']='completed'; break
                time.sleep(.01)
            else: raise TimeoutError('Original 20-minute transition bound reached')
        except BaseException as e:
            report['status']='failed'; report['error']=repr(e); raise
        finally:
            if launcher and launcher.poll() is None:
                subprocess.run(['taskkill','/PID',str(launcher.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                launcher.wait(timeout=10)
            if game_handle:
                if kernel.WaitForSingleObject(game_handle,0)==258:
                    kernel.TerminateProcess(game_handle,0); kernel.WaitForSingleObject(game_handle,10000)
                kernel.CloseHandle(game_handle)
            report['finished_at']=datetime.now(timezone.utc).isoformat()
            write(control/'observer.json',report)
    print(json.dumps({'status':report['status'],'game_continued':report.get('game_alive_five_seconds_after_companion_exit')}),flush=True)

if __name__=='__main__': main()
