"""Summarize the entire extended session and every minute, retaining all stalls."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np
from analyze_playable import cadence, quantiles, rows
from playable_trace import application_present, read_trace_log

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stats(times):
    result = cadence(times)
    times = np.sort(np.unique(times))
    intervals = np.diff(times)
    result['intervals_over_100_ms'] = int((intervals > 100).sum())
    if len(times) >= 2:
        result['observed_span_seconds'] = float((times[-1]-times[0])/1000)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    p.add_argument('--evidence', type=Path, required=True)
    a = p.parse_args()
    root = a.run.resolve()
    manifest = json.loads((root/'launch.json').read_text())
    if manifest.get('status') != 'completed' or not manifest.get('soak_seconds'):
        raise ValueError('Requires a completed extended session')
    trace_log = read_trace_log(root/'present-cpu.log')
    if 'ETW events were lost' in trace_log:
        raise ValueError('Event loss invalidates cadence evidence')
    events = (root/'companion/events.log').read_text()
    native_info = json.loads((root/'companion/run.json').read_text())
    if [native_info['width'], native_info['height']] != [2560, 1440] or native_info['source_pid'] != manifest['pid']:
        raise ValueError('Companion dimensions or source ownership differ from this test')
    began = float(re.search(r'^started ([\d.]+)', events, re.M)[1])
    end = began+manifest['soak_seconds']*1000
    cpu = rows(root/'present-cpu.csv')
    native = rows(root/'companion/frames.csv')
    report = {'schema_version': 1, 'run': root.name, 'status': manifest['status'],
              'scope': manifest['soak_scope'], 'duration_seconds': manifest['soak_seconds'],
              'window_qpc_ms': [began, end], 'scene': manifest['scene'], 'preset': manifest['preset'],
              'dimensions': [2560, 1440], 'mode': manifest['mode'],
              'adapter': native_info['adapter'], 'native_configuration': native_info,
              'configuration_verified': bool(manifest.get('settings_readback')),
              'settings_readback': manifest.get('settings_readback'),
              'processing_hashes': manifest['processing_hashes'],
              'events': events.splitlines(), 'processes': {}, 'minute_samples': [],
              'limitations': ['Presents are not displayed frames or input-to-photon latency.',
                              'Initial 30–60s path followed by stationary camera, not ten minutes of movement.',
                              'One pass; normal Codex/documentation work continued on the CPU; no concurrent GPU experiment or video recording.',
                              'No GPU memory telemetry or manual input, scope/menu or semantic acceptance.'],
              'source_hashes': {}}
    series = {}
    for app, key in [('ArmaReforgerSteam.exe', 'game'), ('enr_companion.exe', 'companion')]:
        named = [x for x in cpu if x['Application'] == app and began <= float(x['QPCTime'])*1000 < end]
        selected = [x for x in named if application_present(x)]
        pids = sorted(set(x['ProcessID'] for x in selected))
        if len(pids) != 1:
            raise ValueError('Expected exactly one owned application PID: '+str(pids))
        if key == 'game' and int(pids[0]) != manifest['pid']:
            raise ValueError('Trace game PID differs from owned process')
        times = np.array([float(x['QPCTime'])*1000 for x in selected])
        series[key] = times
        report['processes'][key] = dict(stats(times), pid=int(pids[0]),
                                        excluded_nonapplication_events=len(named)-len(selected))
    series['native_companion'] = np.array([float(x['present_call_qpc_ms']) for x in native if began <= float(x['present_call_qpc_ms']) < end])
    report['processes']['native_companion'] = stats(series['native_companion'])
    report['gpu_copy_inference_draw_ms'] = quantiles([float(x['gpu_copy_draw_ms']) for x in native if float(x['gpu_copy_draw_ms']) >= 0])
    report['capture_to_present_call_ms'] = quantiles([float(x['capture_to_present_call_ms']) for x in native])
    report['dropped_before_processing'] = sum(int(x['dropped_before']) for x in native)
    for minute in range(manifest['soak_seconds']//60):
        left, right = began+minute*60000, began+(minute+1)*60000
        row = {'minute': minute+1}
        for key, times in series.items():
            selected = times[(times >= left) & (times < right)]
            row[key] = dict(stats(selected), frames_per_declared_60_seconds=len(selected)/60)
        report['minute_samples'].append(row)
    native_summary = report['processes']['native_companion']
    report['acceptance'] = {
        'continuous_runtime_reached': native_summary.get('observed_span_seconds', 0) >= manifest['soak_seconds']-1,
        'all_minutes_at_least_30_native_presents_per_second': all(x['native_companion']['frames_per_declared_60_seconds'] >= 30 for x in report['minute_samples']),
        'no_recorded_hide_or_presentation_timeout': not any('hide ' in x or 'presentation wait timeout' in x for x in report['events']),
        'appearance_goal_complete': False}
    log = sorted((root/'profile/logs').glob('*/script.log'))[-1]
    for path in [root/'launch.json', root/'present-cpu.csv', root/'present-cpu.log', root/'companion/frames.csv', root/'companion/events.log', root/'companion/run.json', log]:
        report['source_hashes'][str(path.relative_to(root)).replace('\\', '/')] = sha(path)
    report['plan_sha256'] = sha(ROOT/'scenes/playable-soak-v1.json')
    a.evidence.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ['processes', 'gpu_copy_inference_draw_ms', 'capture_to_present_call_ms', 'events', 'acceptance']}, indent=2))


if __name__ == '__main__':
    main()
