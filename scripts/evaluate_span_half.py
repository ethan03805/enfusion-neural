"""The single declared FP16 follow-up to the retained SPAN FP32 evaluation."""
import argparse
import json
from pathlib import Path
import sys
import time
import shutil

import numpy as np
from PIL import Image
import onnx
import onnxruntime as ort
from onnxruntime.transformers.float16 import convert_float_to_float16
from onnxruntime.transformers.onnx_model import OnnxModel

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json
from evaluate_span import tensor, metrics, save


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, out / 'driver.py')
    previous = ROOT / 'runs/span-evaluation-v1'; parent = json.loads((previous / 'report.json').read_text())
    if parent['status'] != 'completed' or not parent['restoration_numeric_gate'] or parent['provisional_cost_gate']:
        raise ValueError('Expected useful but over-budget FP32 evaluation')
    if digest(previous / 'model.onnx') != parent['onnx_sha256']: raise ValueError('FP32 model changed')
    report = {'schema_version': 1, 'status': 'started', 'precision': 'FP16 internal / FP32 input and output',
        'parent_report_sha256': digest(previous / 'report.json'), 'driver_sha256': digest(Path(__file__)),
        'adapter': parent['adapter'], 'runtime': ort.__version__, 'plan_sha256': parent['plan_sha256'],
        'timing_scope': parent['timing_scope'], 'images': []}
    write_json(out / 'report.json', report)
    try:
        graph = convert_float_to_float16(onnx.load(previous / 'model.onnx'), keep_io_types=True)
        # ORT 1.19.2 appends I/O Cast nodes; ONNX requires producer-before-consumer order.
        OnnxModel(graph).topological_sort(is_deterministic=True)
        onnx.checker.check_model(graph); onnx.save(graph, out / 'model.onnx')
        report['onnx_sha256'] = digest(out / 'model.onnx')
        options = ort.SessionOptions(); options.enable_mem_pattern = False; options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.enable_profiling = True; options.profile_file_prefix = str(out / 'ort-profile')
        options.add_session_config_entry('session.disable_cpu_ep_fallback', '1')
        began = time.perf_counter()
        session = ort.InferenceSession(str(out / 'model.onnx'), sess_options=options,
            providers=[('DmlExecutionProvider', {'device_id': str(parent['adapter']['index'])})])
        session.disable_fallback(); report['session_setup_ms'] = (time.perf_counter()-began)*1000
        report['providers'] = session.get_providers()
        for i, item in enumerate(parent['images']):
            if digest(ROOT / item['source']) != item['source_sha256']: raise ValueError('Input changed')
            original = Image.open(ROOT / item['source']).convert('RGB'); target = tensor(original)
            low = original.resize((1280, 720), Image.Resampling.BICUBIC); x = tensor(low)
            for _ in range(5 if i == 0 else 1): output = session.run(['output'], {'input': x})[0]
            timings = []
            for _ in range(20 if i == 0 else 5):
                began = time.perf_counter(); output = session.run(['output'], {'input': x})[0]
                timings.append((time.perf_counter()-began)*1000)
            if not np.isfinite(output).all(): raise ValueError('Nonfinite FP16 output')
            np.save(out / f'{i:02d}-raw.npy', output); save(output, out / f'{i:02d}-raw.png')
            row = {'source': item['source'], 'source_sha256': item['source_sha256'], 'timings_ms': timings,
                'median_ms': float(np.median(timings)), 'p95_ms': float(np.percentile(timings, 95)),
                'raw_range': [float(output.min()), float(output.max())],
                'raw_out_of_range_channel_fraction': float(np.mean((output < 0) | (output > 1))),
                'model': metrics(output, target), 'bicubic': item['bicubic'], 'raw_sha256': digest(out / f'{i:02d}-raw.npy')}
            row['psnr_gain_db'] = row['model']['rgb_psnr_db'] - row['bicubic']['rgb_psnr_db']
            if i == 0:
                delta = np.abs(output-np.load(previous / 'cpu-reference.npy'))
                report['cpu_dml_parity'] = {'max_abs': float(delta.max()), 'mean_abs': float(delta.mean()),
                    'passed': bool(delta.max() <= .01 and delta.mean() <= .001)}
            report['images'].append(row); write_json(out / 'report.json', report)
            print(json.dumps(row), flush=True)
        profile = Path(session.end_profiling()); report['profile_file'] = profile.name
        counts = {}
        for e in json.loads(profile.read_text()):
            provider = e.get('args', {}).get('provider')
            if provider: counts[provider] = counts.get(provider, 0)+1
        report['profile_provider_events'] = counts
        if counts.get('CPUExecutionProvider', 0) or not counts.get('DmlExecutionProvider', 0): raise ValueError('Unexpected provider')
        if not report['cpu_dml_parity']['passed']: raise ValueError('FP16 parity failed')
        report['restoration_numeric_gate'] = sum(v['psnr_gain_db'] >= .2 for v in report['images']) >= 3 and report['images'][3]['psnr_gain_db'] >= .2
        report['provisional_cost_gate'] = report['images'][0]['p95_ms'] <= 20
        report['status'] = 'completed'
    except Exception as error:
        report.update(status='failed', error=repr(error)); raise
    finally: write_json(out / 'report.json', report)


if __name__ == '__main__': main()
