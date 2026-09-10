"""Freeze one live release check; retain the original preparation clock."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    plan_path = ROOT/'scenes/playable-live-guard-v1.json'
    if plan_path.exists():
        raise FileExistsError(plan_path)
    source = (ROOT/'scripts/benchmark_playable.py').read_text()
    def replace(old, new):
        nonlocal source
        if source.count(old) != 1:
            raise ValueError('Unexpected benchmark driver: '+old)
        source = source.replace(old, new)
    replace('    argv = [str(game)', '''    frozen_path = ROOT/'scenes/playable-live-guard-v1.json'
    frozen = json.loads(frozen_path.read_text())
    for name, expected_sha in frozen['processing_hashes'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected_sha:
            raise ValueError('Frozen dependency changed: '+name)
    if manifest['addon_hashes'] != frozen['addon_hashes'] or manifest['settings_sha256'] != frozen['settings_sha256']:
        raise ValueError('Private addon/settings differ from retained successful route')
    if (a.scene, a.preset, a.mode, a.record, a.trace) != ('foliage-walk','combined','neural',True,'cpu'):
        raise ValueError('Unexpected live verification configuration')
    manifest['live_guard_plan_sha256'] = hashlib.sha256(frozen_path.read_bytes()).hexdigest()
    argv = [str(game)''')
    replace('    ready = False; recorded = False', '    ready = False; recorded = False; controls_ready = False; companion = None')
    replace('    deadline = time.monotonic() + 160 + a.soak_seconds + (a.sustained_seconds or 0)', '    deadline = time.monotonic() + 360')
    replace('            if a.sustained_seconds:\n                foreground = foreground_pid()', '            if True:\n                foreground = foreground_pid()')
    replace("                    start(companion_command, 'companion-console.log')", "                    companion_command[-1] = '0'\n                    companion_command += ['--snapshot-after','50']\n                    companion = start(companion_command, 'companion-console.log')")
    replace('            if ready and simulation >= stop_simulation: break', '''            if simulation >= 75 and not controls_ready:
                if not (out/'companion/output.bmp').exists():
                    raise RuntimeError('Current native snapshot missing before control checks')
                controls_ready = True
                manifest['controls_ready_simulation_s'] = simulation
                (out/'launch.json').write_text(json.dumps(manifest,indent=2))
                print('CONTROL_CHECKS_READY: measurement and snapshot complete; use F8 twice, F9 twice, then F10 through the game window.',flush=True)
            if companion is not None and companion.poll() is not None:
                if not controls_ready or companion.returncode:
                    raise RuntimeError('Companion exited before controls or unsuccessfully')
                manifest['companion_exit_qpc_ms'] = qpc()
                time.sleep(5)
                manifest['game_alive_five_seconds_after_companion_exit'] = proc.poll() is None
                if proc.poll() is not None:
                    raise RuntimeError('Game did not continue after companion exit')
                break''')
    driver = ROOT/'scripts/verify_live_guard.py'
    driver.write_text(source, encoding='utf-8')
    shader = re.search(r'const char \*shader = R"\((.*?)\)";', (ROOT/'native/companion.cpp').read_text(), re.S).group(1)
    shader_path = ROOT/'runs/live-guard-frozen.hlsl'
    shader_path.write_text(shader,encoding='utf-8')
    prior = json.loads((ROOT/'runs/foliage-walk-neural-v1/launch.json').read_text())
    if prior['status'] != 'completed':
        raise ValueError('Prior route not completed')
    names = ['build/Release/enr_companion.exe','native/companion.cpp','native/curve_network.h',
             'runs/pretrained/zero-dce-plusplus/weights.bin','scripts/verify_live_guard.py',
             'scripts/launch_playable.py','runs/live-guard-frozen.hlsl']
    plan = {'schema_version':1,'started_at':'2026-09-10T13:34:16+00:00','deadline':'2026-09-10T14:04:16+00:00',
            'frozen_at':datetime.now(timezone.utc).isoformat(),'candidate':'Committed channel headroom guard only, strength 0.35',
            'processing_hashes':{n:sha(ROOT/n) for n in names},'addon_hashes':prior['addon_hashes'],
            'settings_sha256':prior['settings_sha256'],'prior_successful_route':'runs/foliage-walk-neural-v1/launch.json',
            'prior_route_sha256':sha(ROOT/'runs/foliage-walk-neural-v1/launch.json'),
            'window_simulation_s':[30,60],'recording_s':[28,62],'snapshot_after_companion_s':50,
            'gates':{'game_and_companion_min_present_fps':30,'game_and_companion_max_p95_interval_ms':33.3,
                     'snapshot_replay_rgb8_max_error':0,'snapshot_replay_curve_max_error':0,'independent_cpu_curve_max_error':0.0001,
                     'newly_clipped_channels':0,'protected_rgb8_max_error':0,'max_rgb8_change':15,
                     'unintended_fallback_or_timeout_in_measurement':0,'game_foreground_entire_measurement':True},
            'controls':'After simulation 75: observed F8 bypass/resume, both F9 modes, F10 exit and original game alive five seconds later. Automated hotkeys do not establish physical WASD/mouse routing.',
            'recording':'Original timestamp VFR 1440p AMF recording. Report recording cost as included, without unpaired subtraction. Review chronological samples and native keys; do not claim full perceptual playback.',
            'failure_policy':'No second candidate, changed gates or new baseline to extend the original 30 minutes. Keep old download unless every live gate passes.',
            'limits':'Software Present age only; display and physical input latency unavailable. This correction supplies no substantial material/lighting gain.'}
    plan_path.write_text(json.dumps(plan,indent=2),encoding='utf-8')
    print(json.dumps({'plan_sha256':sha(plan_path),'frozen_at':plan['frozen_at'],'deadline':plan['deadline']}))

if __name__ == '__main__':
    main()
