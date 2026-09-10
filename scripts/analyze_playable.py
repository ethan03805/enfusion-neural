"""Report a fixed simulation-second 30..60 path; do not substitute dispatch FPS."""
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

import numpy as np
from playable_trace import application_present, read_trace_log


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def quantiles(values):
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if not len(x): return None
    return dict(zip(['min', 'p50', 'p95', 'p99', 'max'], map(float, np.percentile(x, [0, 50, 95, 99, 100]))))


def cadence(times):
    times = np.sort(np.unique(times))
    if len(times) < 2: return {'frames': len(times)}
    intervals = np.diff(times)
    return {'frames': len(times), 'mean_fps': float(1000*(len(times)-1)/(times[-1]-times[0])), 'interval_ms': quantiles(intervals), 'intervals_over_33_333_ms': int((intervals>1000/30).sum()), 'intervals_over_50_ms': int((intervals>50).sum())}


def analyze(root):
    manifest = json.loads((root/'launch.json').read_text())
    display_only_failure = manifest.get('error') == "RuntimeError('Missing nonempty present-display trace')"
    if manifest.get('status') != 'completed' and not display_only_failure: raise ValueError('Run not completed')
    for file in root.glob('present-*.log'):
        if 'ETW events were lost' in read_trace_log(file): raise ValueError('ETW event loss invalidates measurements')
    log = sorted((root/'profile/logs').glob('*/script.log'))[-1]
    day = log.parent.name.split('_')[1]
    trace = []
    pattern = r'(\d{2}:\d{2}:\d{2}\.\d+) SCRIPT\s+: ENR_LIVE simulation_s=([\d.]+) frame=(\d+) dt_ms=([\d.]+) camera=<([^>]+)> direction=<([^>]+)>'
    for m in re.finditer(pattern, log.read_text(errors='replace')):
        local = datetime.fromisoformat(day+'T'+m[1]).timestamp()
        at = manifest['qpc_anchor_ms'] + (local-manifest['created_unix_s'])*1000
        trace.append({'simulation_s': float(m[2]), 'qpc_ms': at, 'frame': int(m[3]), 'camera': list(map(float, m[5].split(','))), 'direction': list(map(float, m[6].split(',')))})
    simulation = [r['simulation_s'] for r in trace]
    qpcs = [r['qpc_ms'] for r in trace]
    if not simulation or max(simulation)<60: raise ValueError('Missing complete path')
    start, end = np.interp([30,60], simulation, qpcs)
    report = {'schema_version': 1, 'run': root.name, 'scene': manifest['scene'], 'preset': manifest['preset'], 'mode': manifest['mode'], 'recording': manifest['recording'], 'window': {'simulation_s': [30,60], 'qpc_ms': [float(start),float(end)], 'alignment': 'Interpolation of game log simulation timestamps; local clock mapped to QPC at launch. Millisecond log precision; not input-to-photon.'}, 'game': {}, 'companion': {}, 'path': [r for r in trace if 29<=r['simulation_s']<=61], 'source_hashes': {}}
    report['settings_readback'] = manifest.get('settings_readback')
    report['configuration_verified'] = bool(manifest.get('settings_readback'))
    cpu = rows(root/'present-cpu.csv') if (root/'present-cpu.csv').exists() else []
    if not cpu and manifest.get('trace')!='display': raise ValueError('Missing CPU trace')
    display = rows(root/'present-display.csv') if (root/'present-display.csv').exists() else []
    report['measurement_status'] = manifest.get('status')
    report['display_trace_available'] = bool(display)
    def in_window(r): return start<=float(r['QPCTime'])*1000<end
    for exe, key in [('ArmaReforgerSteam.exe','game'), ('enr_companion.exe','companion')]:
        candidates_cpu = [r for r in cpu if r['Application']==exe and in_window(r)]
        observed = [r for r in candidates_cpu if application_present(r)]
        summary = cadence([float(r['QPCTime'])*1000 for r in observed])
        summary['excluded_nonapplication_records'] = len(candidates_cpu)-len(observed)
        summary['scope'] = 'DXGI application Present calls including non-displayed frames; GPU and display tracking disabled in separate CPU trace'
        shown = [r for r in display if r['Application']==exe and in_window(r) and application_present(r)]
        summary['display_trace_rows'] = len(shown)
        summary['display_trace_dropped'] = sum(r['Dropped']=='1' for r in shown)
        summary['gpu_active_ms'] = quantiles([float(r['msGPUActive']) for r in shown])
        if not shown: summary['gpu_limitation'] = 'PresentMon display/GPU tracking did not resolve this application in the measured window; no per-application GPU duration claimed'
        report[key] = summary
    if (root/'companion/frames.csv').exists():
        native = sorted(rows(root/'companion/frames.csv'), key=lambda r: float(r['present_call_qpc_ms']))
        selected = [r for r in native if start<=float(r['present_call_qpc_ms'])<end]
        report['companion']['native_present_cadence'] = cadence([float(r['present_call_qpc_ms']) for r in selected])
        report['companion']['gpu_copy_inference_draw_ms'] = quantiles([float(r['gpu_copy_draw_ms']) for r in selected if float(r['gpu_copy_draw_ms'])>=0])
        report['companion']['capture_to_present_call_ms'] = quantiles([float(r['capture_to_present_call_ms']) for r in selected])
        report['companion']['dropped_before_processing'] = sum(int(r['dropped_before']) for r in selected)
        times = np.array([float(r['present_call_qpc_ms']) for r in native])
        latencies, residuals = [], []
        candidates = [r for r in display if r['Application']=='enr_companion.exe' and r['Dropped']=='0' and in_window(r)]
        for r in candidates:
            at = float(r['QPCTime'])*1000
            i = int(np.argmin(abs(times-at)))
            residual = abs(times[i]-at)
            if residual>1: continue
            age = at+float(r['msUntilDisplayed'])-float(native[i]['capture_qpc_ms'])
            residuals.append(float(residual)); latencies.append(age)
        report['companion']['capture_to_display'] = {'scope': 'WGC compositor frame timestamp to PresentMon reported display; excludes input sampling and physical panel response', 'eligible_displayed_frames': len(candidates), 'joined_frames': len(latencies), 'join_residual_ms': quantiles(residuals), 'latency_ms': quantiles(latencies)}
    for file in [root/'launch.json', log, root/'present-cpu.csv', root/'present-display.csv', root/'companion/frames.csv', root/'companion/events.log']:
        if file.exists(): report['source_hashes'][str(file.relative_to(root))] = hashlib.sha256(file.read_bytes()).hexdigest()
    (root/'analysis.json').write_text(json.dumps(report, indent=2))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('runs', nargs='+', type=Path)
    for path in p.parse_args().runs:
        r = analyze(path)
        print(json.dumps({k:r[k] for k in ['run','scene','preset','mode','recording','game','companion']}, indent=2))


if __name__ == '__main__': main()
