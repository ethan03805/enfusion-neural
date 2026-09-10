"""Audit the bounded DXGI counter probes without inventing display timestamps."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import subprocess

from analyze_playable import analyze, quantiles

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', nargs='+', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--plan', type=Path, default=ROOT / 'scenes/playable-dxgi-statistics-v1.json')
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    plan = json.loads(args.plan.read_text())
    if len(args.runs) > plan['maximum_probe_runs']:
        raise ValueError('Declared probe count exceeded')
    report = {'schema_version': 1, 'date': '2026-09-10', 'plan': plan,
              'plan_sha256': sha(args.plan), 'runs': [],
              'scope': 'Diagnostic OS swapchain queries alongside actual 1440p gameplay. No displayed FPS or latency can be calculated from zero display counters. DwmFlush changes scheduling; do not treat its cadence as the normal companion.'}
    fields = ['display_present_count', 'present_refresh_count', 'sync_refresh_count', 'sync_qpc_ticks']
    for path in args.runs:
        root = path.resolve()
        measurement = analyze(root)
        launch = json.loads((root / 'launch.json').read_text())
        native = json.loads((root / 'companion/run.json').read_text())
        if not native['frame_statistics'] or measurement['recording']:
            raise ValueError('Wrong probe configuration')
        if (measurement['scene'], measurement['preset'], measurement['mode']) != (plan['scene'], plan['preset'], plan['mode']):
            raise ValueError('Probe differs from plan')
        source = root / 'companion/display-statistics.csv'
        with source.open(newline='') as f:
            rows = list(csv.DictReader(f))
        if not rows or [int(r['frame']) for r in rows] != list(range(len(rows))):
            raise ValueError('Incomplete or duplicate per-frame query log')
        good = [r for r in rows if int(r['statistics_hresult']) == 0]
        informative = [r for r in good if all(int(r[k]) > 0 for k in fields)]
        queries = [float(r['query_end_qpc_ms']) - float(r['query_start_qpc_ms']) for r in rows]
        if min(queries) < 0:
            raise ValueError('Backwards query clock')
        files = [root / 'launch.json', source, root / 'companion/run.json', root / 'companion/events.log', root / 'companion/frames.csv']
        report['runs'].append({
            'run': root.name, 'adapter': native['adapter'], 'dimensions': [native['width'], native['height']],
            'precision': native['precision'], 'qpc_frequency_hz': native['qpc_frequency_hz'],
            'dwm_flush': native['frame_statistics_dwm_flush'], 'processed_frames_and_queries': len(rows),
            'statistics_hresult_counts': dict(Counter(f"0x{int(r['statistics_hresult']):08X}" for r in rows)),
            'last_present_hresult_counts': dict(Counter(f"0x{int(r['last_present_hresult']):08X}" for r in rows)),
            'flush_hresult_counts': dict(Counter(f"0x{int(r['flush_hresult']):08X}" for r in rows)),
            'last_present_count_range': [min(int(r['last_present_count']) for r in rows), max(int(r['last_present_count']) for r in rows)],
            'successful_statistics_calls': len(good), 'informative_statistics_calls': len(informative),
            'successful_counter_ranges': {k: [min(int(r[k]) for r in good), max(int(r[k]) for r in good)] if good else None for k in fields},
            'query_including_optional_flush_ms': quantiles(queries), 'raw_query_durations_ms': queries,
            'measurement': measurement, 'processing_hashes': launch['processing_hashes'],
            'source_hashes': {str(f.relative_to(ROOT)).replace('\\', '/'): sha(f) for f in files}})
    all_zero = all(r['successful_statistics_calls'] > 0 and all(v == [0, 0] for v in r['successful_counter_ranges'].values()) for r in report['runs'])
    both_modes = {r['dwm_flush'] for r in report['runs']} == {False, True}
    report['outcome'] = ('closed_no_display_counters' if all_zero and both_modes else 'requires_counter_review')
    report['display_latency_ms'] = None
    report['explanation'] = ('Both probes returned one initial DXGI_ERROR_FRAME_STATISTICS_DISJOINT followed by S_OK with all display counters zero. GetLastPresentCount advanced, proving submitted calls only. DwmFlush did not make the counters usable. Stop this route after the two declared probes; keep the earlier separate PresentMon display evidence and label moving-path display latency unavailable.' if all_zero and both_modes else 'Do not infer display latency until the raw counters are independently reviewed and mapped.')
    # This diagnostic changes CPU telemetry only. Verify the GPU code remained exact.
    before = subprocess.check_output(['git', 'show', 'd52a2ae:native/companion.cpp'], cwd=ROOT, text=True)
    after = (ROOT / 'native/companion.cpp').read_text()
    shader = lambda text: text.split('const char *shader = R"(', 1)[1].split(')";', 1)[0]
    if shader(before) != shader(after):
        raise ValueError('Presentation shader changed during telemetry probe')
    report['unchanged_gpu_shader_sha256'] = hashlib.sha256(shader(after).encode()).hexdigest()
    report['source_hashes'] = {str(f.relative_to(ROOT)).replace('\\', '/'): sha(f) for f in [ROOT / 'native/companion.cpp', ROOT / 'native/curve_network.h', ROOT / 'scripts/benchmark_playable.py', Path(__file__).resolve()]}
    previous = ROOT / 'runs/companion-before-dxgi-statistics-v1/enr_companion.exe'
    report['retained_nonprobe_binary_sha256'] = sha(previous)
    report['download_change'] = 'None. Optional diagnostic flags are off by default; the previously verified package remains unchanged.'
    args.out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'outcome': report['outcome'], 'runs': [{k: r[k] for k in ['run', 'processed_frames_and_queries', 'statistics_hresult_counts', 'informative_statistics_calls', 'query_including_optional_flush_ms']} for r in report['runs']]}, indent=2))


if __name__ == '__main__':
    main()
