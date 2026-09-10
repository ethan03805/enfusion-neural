"""Serial isolated gameplay measurement. Run one instance; retain every run."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

from launch_playable import ROOT, SCENES, prepare
from playable_trace import read_trace_log


def qpc():
    value, frequency = ctypes.c_longlong(), ctypes.c_longlong()
    ctypes.windll.kernel32.QueryPerformanceCounter(ctypes.byref(value))
    ctypes.windll.kernel32.QueryPerformanceFrequency(ctypes.byref(frequency))
    return value.value * 1000 / frequency.value


def foreground_pid():
    """Read foreground ownership for measurement; never activate a window."""
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = ctypes.c_void_p
    user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    value = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), ctypes.byref(value))
    return value.value


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--scene', choices=SCENES, default='town')
    p.add_argument('--preset', choices=['standard', 'scale', 'shadows', 'effects', 'combined'], default='standard')
    p.add_argument('--mode', choices=['off', 'identity', 'neural'], default='off')
    p.add_argument('--record', action='store_true')
    p.add_argument('--trace', choices=['cpu','display','both'], default='both')
    p.add_argument('--frame-statistics', choices=['off', 'poll', 'flush'], default='off', help='Optional DXGI display-counter probe; flush adds DwmFlush synchronization and changes scheduling')
    p.add_argument('--soak-seconds', type=int, default=0, help='Extended runtime check after the existing 30–60s path; remaining time is stationary. Zero keeps the original benchmark.')
    p.add_argument('--sustained-validation', type=Path, help='Successful Enfusion Lab validation run containing the exact sustained-route addon')
    p.add_argument('--sustained-seconds', type=int, choices=[84,180], help='Two-cycle pilot or full sustained movement measurement')
    p.add_argument('--sustained-plan', type=Path, default=ROOT/'scenes/playable-sustained-v1.json')
    a = p.parse_args()
    if bool(a.sustained_validation) != bool(a.sustained_seconds): p.error('Sustained route requires both validation run and duration')
    if a.sustained_seconds and (a.soak_seconds or a.scene != 'foliage-walk' or a.trace != 'cpu' or a.frame_statistics != 'off'):
        p.error('Sustained route requires foliage-walk, CPU trace, no soak or frame-statistics probe')
    if a.mode == 'off' and a.frame_statistics != 'off': p.error('Frame statistics require a running companion')
    if a.soak_seconds and not 60 <= a.soak_seconds <= 1800: p.error('Soak duration must be 60..1800 seconds')
    if a.soak_seconds and a.record: p.error('Soak measurement excludes recording')
    processes = subprocess.check_output(['tasklist','/FI','IMAGENAME eq ArmaReforgerSteam.exe','/FO','CSV','/NH'], text=True)
    if 'ArmaReforgerSteam.exe' in processes: raise RuntimeError('Close the existing game before starting a benchmark')
    out = a.out.resolve()
    game = Path('C:/Program Files (x86)/Steam/steamapps/common/Arma Reforger/ArmaReforgerSteam.exe')
    user = Path(os.environ['USERPROFILE'])
    sources = [x for d in [user/'OneDrive/Documents', user/'Documents'] for x in (d/'My Games/ArmaReforger/profile/.save').glob('*/settings/ReforgerEngineSettings.conf')]
    if not sources: raise RuntimeError('No saved settings profile')
    addon, manifest = prepare(out, a.scene, a.preset, True, sources[0])
    shutil.copyfile(__file__, out/'benchmark-driver.py')
    manifest['benchmark_driver_sha256'] = hashlib.sha256((out/'benchmark-driver.py').read_bytes()).hexdigest()
    if a.sustained_validation:
        validation = a.sustained_validation.resolve()
        valid = json.loads((validation/'run.json').read_text())
        if valid['command'] != 'validate' or valid['status'] != 'succeeded' or valid['process_exit_code'] != 0 or valid['terminated_owned_process']:
            raise ValueError('Unverified sustained addon')
        for name, sha in valid['addon_sha256'].items():
            source = validation/'addon'/name
            if hashlib.sha256(source.read_bytes()).hexdigest() != sha: raise ValueError('Changed validated addon')
            target = addon/name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        actual = {f.relative_to(addon).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest() for f in addon.rglob('*') if f.is_file()}
        if actual != valid['addon_sha256']: raise ValueError('Gameplay addon differs from validated snapshot')
        manifest.update(addon_hashes=actual, automatic=False, sustained_seconds=a.sustained_seconds,
                        sustained_validation=validation.as_posix(), sustained_validation_sha256=hashlib.sha256((validation/'run.json').read_bytes()).hexdigest(),
                        sustained_plan_sha256=hashlib.sha256(a.sustained_plan.read_bytes()).hexdigest())
    argv = [str(game), '-profile', str(out/'profile'), '-gproj', str(addon/'addon.gproj'), '-addonsDir', str(game.parent/'addons'), '-world', 'worlds/GameMaster/GM_Eden.ent', '-play', '-nosplash', '-maxFPS', '120']
    manifest.update(created_unix_s=time.time(), qpc_anchor_ms=qpc(), mode=a.mode, recording=a.record, trace=a.trace, argv=argv)
    manifest['soak_seconds'] = a.soak_seconds
    manifest['frame_statistics'] = a.frame_statistics
    if a.soak_seconds:
        manifest['soak_scope'] = 'Existing walking/turning path at simulation 30–60 seconds, then stationary town camera. Continuous runtime/cadence check; not ten minutes of movement, manual input or semantic acceptance.'
    manifest['processing_hashes']={str(f.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in [ROOT/'build/Release/enr_companion.exe',ROOT/'native/companion.cpp',ROOT/'native/curve_network.h',ROOT/'runs/pretrained/zero-dce-plusplus/weights.bin']}
    tasks, handles = [], []
    proc = subprocess.Popen(argv, cwd=game.parent)
    manifest['pid'] = proc.pid
    manifest['commands'] = []
    manifest['foreground_changes'] = []
    (out/'launch.json').write_text(json.dumps(manifest, indent=2))

    def start(command, log):
        h = open(out/log, 'w', encoding='utf-8'); handles.append(h)
        manifest['commands'].append(dict(argv=list(map(str, command)), unix_s=time.time(), qpc_ms=qpc()))
        child = subprocess.Popen(list(map(str, command)), stdout=h, stderr=subprocess.STDOUT)
        tasks.append(child)
        return child

    ready = False; recorded = False
    deadline = time.monotonic() + 160 + a.soak_seconds + (a.sustained_seconds or 0)
    stop_simulation = 38 + a.sustained_seconds if a.sustained_seconds else 68
    try:
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                manifest['early_game_exit_code'] = proc.returncode
                raise RuntimeError('Game exited before benchmark completed')
            logs = list((out/'profile/logs').glob('*/script.log'))
            text = logs[-1].read_text(errors='replace') if logs else ''
            stamps = re.findall(r'ENR_LIVE simulation_s=([0-9.]+)', text)
            simulation = float(stamps[-1]) if stamps else 0
            if a.sustained_seconds:
                foreground = foreground_pid()
                if not manifest['foreground_changes'] or manifest['foreground_changes'][-1]['pid'] != foreground:
                    manifest['foreground_changes'].append({'simulation_s':simulation,'qpc_ms':qpc(),'pid':foreground})
            if simulation >= 18 and not ready:
                if 'controlled=1' not in text: raise RuntimeError('No controlled player')
                if a.sustained_seconds and foreground != proc.pid:
                    raise RuntimeError('Game is not foreground at benchmark start; no controlled comparison recorded')
                settings = {}
                for event in re.findall(r'ENR (\{"protocol":2,"event":"setting"[^\n]+\})', text):
                    item = json.loads(event)
                    settings[item['module']+'.'+item['key']] = item['value']
                expected = {'VideoUserSettings.ResolutionScale': .75 if a.preset in ['scale','combined'] else 1,
                            'VideoUserSettings.FsrEnabled': int(a.preset in ['scale','combined']),
                            'PipelineUserSettings.ShadowQuality': 2 if a.preset in ['shadows','combined'] else 3,
                            'VideoUserSettings.DistantShadowsQuality': 1 if a.preset in ['shadows','combined'] else 3}
                if a.preset in ['effects','combined']:
                    expected.update({'PPEffectsSettings.SSDO': 0, 'PPEffectsSettings.SSR': 0})
                manifest['settings_readback'] = settings
                mismatches = {k: {'expected':v,'actual':settings.get(k)} for k,v in expected.items() if settings.get(k)!=v}
                if mismatches: raise RuntimeError('Requested settings not active: '+json.dumps(mismatches))
                if a.mode != 'off':
                    companion_duration = a.sustained_seconds + 18 if a.sustained_seconds else (a.soak_seconds or 49)
                    companion_command = [ROOT/'build/Release/enr_companion.exe', '--pid', proc.pid, '--out', out/'companion', '--overlay', '--mode', a.mode, '--model', ROOT/'runs/pretrained/zero-dce-plusplus/weights.bin', '--seconds', str(companion_duration)]
                    if a.frame_statistics != 'off':
                        companion_command.append('--frame-statistics' if a.frame_statistics == 'poll' else '--frame-statistics-flush')
                    start(companion_command, 'companion-console.log')
                pm = ROOT/'runs/tools/PresentMon-2.5.1-x64.exe'
                trace_duration = a.sustained_seconds + 18 if a.sustained_seconds else (a.soak_seconds or 47)
                base = [pm, '--process_name', 'ArmaReforgerSteam.exe', '--process_name', 'enr_companion.exe', '--qpc_time_ms', '--v1_metrics', '--timed', str(trace_duration), '--terminate_after_timed', '--no_console_stats', '--no_track_input']
                if a.trace in ['display','both']:
                    start(base+['--output_file', out/'present-display.csv', '--session_name', 'ENR_display_'+str(proc.pid)], 'present-display.log')
                if a.trace in ['cpu','both']:
                    start(base+['--output_file', out/'present-cpu.csv', '--session_name', 'ENR_cpu_'+str(proc.pid), '--no_track_gpu', '--no_track_display'], 'present-cpu.log')
                manifest['ready_simulation_s'] = simulation
                if a.soak_seconds: stop_simulation = simulation + a.soak_seconds + 2
                ready = True
                print(f'{out.name}: player ready; measurement started at simulation {simulation:.3f}s', flush=True)
            if a.record and simulation >= 28 and not recorded:
                if a.sustained_seconds and a.mode != 'off':
                    frames = out/'companion/frames.csv'
                    if not frames.exists() or frames.stat().st_size < 1024:
                        raise RuntimeError('Companion produced no verified frames before recording; preserve startup evidence')
                target = 'ArmaReforgerSteam.exe' if a.mode == 'off' else 'enr_companion.exe'
                record_duration = a.sustained_seconds + 4 if a.sustained_seconds else 34
                start(['ffmpeg', '-hide_banner', '-f', 'lavfi', '-i', f'gfxcapture=window_exe={target}:max_framerate=60:capture_cursor=0:display_border=0', '-vf', 'hwdownload,format=bgra,scale=in_range=full:out_range=tv:out_color_matrix=bt709,format=nv12', '-t', str(record_duration), '-an', '-c:v', 'h264_amf', '-b:v', '25M', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'iec61966-2-1', '-fps_mode', 'vfr', out/'gameplay.mp4'], 'recording.log')
                manifest['record_start_simulation_s'] = simulation
                recorded = True
            if ready and simulation >= stop_simulation: break
            time.sleep(.05)
        else: raise TimeoutError('Gameplay measurement exceeded its bounded deadline')
        for t in tasks:
            t.wait(timeout=10)
            if t.returncode: raise RuntimeError(f'Capture child failed: {t.returncode}')
        manifest['trace_availability'] = {}
        for name in ['present-cpu','present-display']:
            if a.trace!='both' and name!='present-'+a.trace: continue
            file = out/(name+'.csv')
            available = file.exists() and file.stat().st_size>=100
            manifest['trace_availability'][name] = available
            if not available and name=='present-cpu': raise RuntimeError('Missing nonempty '+name+' trace')
            if 'ETW events were lost' in read_trace_log(out/(name+'.log')): raise RuntimeError('ETW event loss invalidates '+name+' measurement')
        manifest['status'] = 'completed'
        print(f'{out.name}: completed; retained raw game, companion and recording evidence', flush=True)
    except Exception as e:
        manifest['status'] = 'failed'; manifest['error'] = repr(e)
        raise
    finally:
        for t in tasks:
            if t.poll() is None: t.terminate(); t.wait(timeout=10)
        if proc.poll() is None: proc.terminate(); proc.wait(timeout=15)
        # A terminated PresentMon process can leave a kernel ETW session behind.
        # Stop only this run's two uniquely named measurement sessions.
        for name in ['ENR_display_'+str(proc.pid), 'ENR_cpu_'+str(proc.pid)]:
            subprocess.run([str(ROOT/'runs/tools/PresentMon-2.5.1-x64.exe'), '--session_name', name, '--terminate_existing_session'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for h in handles: h.close()
        manifest['finished_unix_s'] = time.time()
        (out/'launch.json').write_text(json.dumps(manifest, indent=2))


if __name__ == '__main__': main()
