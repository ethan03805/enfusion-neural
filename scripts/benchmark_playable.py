"""Serial isolated gameplay measurement. Run one instance; retain every run."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import re
import subprocess
import time

from launch_playable import ROOT, SCENES, prepare


def qpc():
    value, frequency = ctypes.c_longlong(), ctypes.c_longlong()
    ctypes.windll.kernel32.QueryPerformanceCounter(ctypes.byref(value))
    ctypes.windll.kernel32.QueryPerformanceFrequency(ctypes.byref(frequency))
    return value.value * 1000 / frequency.value


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--scene', choices=SCENES, default='town')
    p.add_argument('--preset', choices=['standard', 'scale', 'shadows', 'effects', 'combined'], default='standard')
    p.add_argument('--mode', choices=['off', 'identity', 'neural'], default='off')
    p.add_argument('--record', action='store_true')
    a = p.parse_args()
    out = a.out.resolve()
    game = Path('C:/Program Files (x86)/Steam/steamapps/common/Arma Reforger/ArmaReforgerSteam.exe')
    user = Path(os.environ['USERPROFILE'])
    sources = [x for d in [user/'OneDrive/Documents', user/'Documents'] for x in (d/'My Games/ArmaReforger/profile/.save').glob('*/settings/ReforgerEngineSettings.conf')]
    if not sources: raise RuntimeError('No saved settings profile')
    addon, manifest = prepare(out, a.scene, a.preset, True, sources[0])
    argv = [str(game), '-profile', str(out/'profile'), '-gproj', str(addon/'addon.gproj'), '-addonsDir', str(game.parent/'addons'), '-world', 'worlds/GameMaster/GM_Eden.ent', '-play', '-nosplash', '-maxFPS', '120']
    manifest.update(created_unix_s=time.time(), qpc_anchor_ms=qpc(), mode=a.mode, recording=a.record, argv=argv)
    tasks, handles = [], []
    proc = subprocess.Popen(argv, cwd=game.parent)
    manifest['pid'] = proc.pid
    manifest['commands'] = []
    (out/'launch.json').write_text(json.dumps(manifest, indent=2))

    def start(command, log):
        h = open(out/log, 'w', encoding='utf-8'); handles.append(h)
        manifest['commands'].append(dict(argv=list(map(str, command)), unix_s=time.time(), qpc_ms=qpc()))
        child = subprocess.Popen(list(map(str, command)), stdout=h, stderr=subprocess.STDOUT)
        tasks.append(child)
        return child

    ready = False; recorded = False
    deadline = time.monotonic() + 160
    try:
        while time.monotonic() < deadline:
            if proc.poll() is not None: raise RuntimeError('Game exited before benchmark completed')
            logs = list((out/'profile/logs').glob('*/script.log'))
            text = logs[-1].read_text(errors='replace') if logs else ''
            stamps = re.findall(r'ENR_LIVE simulation_s=([0-9.]+)', text)
            simulation = float(stamps[-1]) if stamps else 0
            if simulation >= 18 and not ready:
                if 'controlled=1' not in text: raise RuntimeError('No controlled player')
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
                    start([ROOT/'build/Release/enr_companion.exe', '--pid', proc.pid, '--out', out/'companion', '--overlay', '--mode', a.mode, '--model', ROOT/'runs/pretrained/zero-dce-plusplus/weights.bin', '--seconds', '49'], 'companion-console.log')
                pm = ROOT/'runs/tools/PresentMon-2.5.1-x64.exe'
                base = [pm, '--process_name', 'ArmaReforgerSteam.exe', '--process_name', 'enr_companion.exe', '--qpc_time_ms', '--v1_metrics', '--timed', '47', '--terminate_after_timed', '--no_console_stats', '--no_track_input']
                start(base+['--output_file', out/'present-display.csv', '--session_name', 'ENR_display_'+str(proc.pid)], 'present-display.log')
                start(base+['--output_file', out/'present-cpu.csv', '--session_name', 'ENR_cpu_'+str(proc.pid), '--no_track_gpu', '--no_track_display'], 'present-cpu.log')
                manifest['ready_simulation_s'] = simulation
                ready = True
                print(f'{out.name}: player ready; measurement started at simulation {simulation:.3f}s', flush=True)
            if a.record and simulation >= 28 and not recorded:
                target = 'ArmaReforgerSteam.exe' if a.mode == 'off' else 'enr_companion.exe'
                start(['ffmpeg', '-hide_banner', '-f', 'lavfi', '-i', f'gfxcapture=window_exe={target}:max_framerate=60:capture_cursor=0:display_border=0', '-vf', 'hwdownload,format=bgra,scale=in_range=full:out_range=tv:out_color_matrix=bt709,format=nv12', '-t', '34', '-an', '-c:v', 'h264_amf', '-b:v', '25M', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'iec61966-2-1', '-fps_mode', 'vfr', out/'gameplay.mp4'], 'recording.log')
                manifest['record_start_simulation_s'] = simulation
                recorded = True
            if ready and simulation >= 68: break
            time.sleep(.05)
        else: raise TimeoutError('No completed gameplay path within 160 seconds')
        for t in tasks:
            t.wait(timeout=10)
            if t.returncode: raise RuntimeError(f'Capture child failed: {t.returncode}')
        manifest['trace_availability'] = {}
        for name in ['present-cpu','present-display']:
            file = out/(name+'.csv')
            available = file.exists() and file.stat().st_size>=100
            manifest['trace_availability'][name] = available
            if not available and name=='present-cpu': raise RuntimeError('Missing nonempty '+name+' trace')
            if 'ETW events were lost' in (out/(name+'.log')).read_text(): raise RuntimeError('ETW event loss invalidates '+name+' measurement')
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
