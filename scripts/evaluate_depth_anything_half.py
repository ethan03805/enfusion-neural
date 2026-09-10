"""One FP16 conversion of the retained 392-short-side depth graph."""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

import numpy as np
import onnx
import onnxruntime as ort
from onnxruntime.transformers.float16 import convert_float_to_float16
from onnxruntime.transformers.onnx_model import OnnxModel
from PIL import Image
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, out/'driver.py')
    previous = ROOT/'runs/depth-anything-392-v1'
    parent = json.loads((previous/'report.json').read_text())
    plan_path = ROOT/'scenes/playable-depth-evaluation-v1.json'
    plan = json.loads(plan_path.read_text())
    report = {'schema_version': 1, 'status': 'started', 'short_side': 392,
        'precision': 'FP16 internal / FP32 input and output', 'images': [],
        'driver_sha256': digest(Path(__file__)), 'plan_sha256': digest(plan_path),
        'parent_report_sha256': digest(previous/'report.json')}
    write_json(out/'report.json', report)
    try:
        if parent['status'] != 'completed' or parent['provisional_cost_pass'] or not parent['parity_pass']:
            raise ValueError('Expected parity-passing, over-budget FP32 parent')
        if digest(previous/'model.onnx') != parent['onnx_sha256']: raise ValueError('Changed graph')
        if report['plan_sha256'] != parent['plan_sha256']: raise ValueError('Changed plan')
        active = subprocess.check_output(['powershell','-NoProfile','-Command',
            'Get-Process -Name ArmaReforgerSteam,ArmaReforgerWorkbenchSteamDiag,enr_companion -ErrorAction SilentlyContinue | Select-Object -ExpandProperty ProcessName; exit 0'],text=True).strip()
        if active: raise ValueError('GPU session still active: '+active)
        report['adapter_info'] = subprocess.check_output([str(ROOT/'build/Release/enr_adapter_info.exe')], text=True)
        if json.loads(report['adapter_info'].splitlines()[0])['description'] != 'AMD Radeon RX 7800 XT': raise ValueError('Unexpected adapter 0')
        report['software'] = parent['software']
        graph = convert_float_to_float16(onnx.load(previous/'model.onnx'), keep_io_types=True)
        OnnxModel(graph).topological_sort(is_deterministic=True)
        onnx.checker.check_model(graph); onnx.save(graph, out/'model.onnx')
        report['onnx_sha256'] = digest(out/'model.onnx')
        options = ort.SessionOptions(); options.enable_mem_pattern = False
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.add_session_config_entry('session.disable_cpu_ep_fallback', '1')
        options.enable_profiling = True; options.profile_file_prefix = str(out/'profile')
        session = ort.InferenceSession(str(out/'model.onnx'), sess_options=options,
            providers=[('DmlExecutionProvider', {'device_id': 0})])
        session.disable_fallback(); report['providers'] = session.get_providers()
        for i, original in enumerate(parent['images']):
            for suffix in ['input', 'cpu']:
                if digest(previous/f'{i:02d}-{suffix}.npy') != original[f'{suffix}_sha256']: raise ValueError('Changed input/reference')
            feed = {'rgb': np.load(previous/f'{i:02d}-input.npy')}
            ref = np.load(previous/f'{i:02d}-cpu.npy')
            for _ in range(5 if i == 0 else 1): session.run(None, feed)
            timings = []
            for _ in range(20 if i == 0 else 5):
                start = time.perf_counter(); output = session.run(None, feed)[0]
                timings.append((time.perf_counter()-start)*1000)
            if not np.isfinite(output).all(): raise ValueError('Nonfinite FP16 prediction')
            np.save(out/f'{i:02d}-dml.npy', output)
            error = np.abs(output-ref); scale = max(float(np.ptp(ref)), 1e-6)
            limits = plan['parity_limits']
            row = {k: original[k] for k in ['name','source','source_sha256','tensor_shape','source_height_width','input_sha256','cpu_sha256']}
            row.update(milliseconds=timings, median_ms=float(np.median(timings)), p95_ms=float(np.percentile(timings,95)),
                range=[float(output.min()),float(output.max())], dml_sha256=digest(out/f'{i:02d}-dml.npy'),
                parity={'raw_max':float(error.max()),'raw_mean':float(error.mean()),'cpu_range':scale,
                    'normalized_max':float(error.max())/scale,'normalized_mean':float(error.mean())/scale,
                    'passed':bool(error.max()/scale <= limits['fp16_normalized_max'] and error.mean()/scale <= limits['fp16_normalized_mean'])})
            with torch.inference_mode(): full = F.interpolate(torch.from_numpy(output)[:,None],tuple(row['source_height_width']),mode='bilinear',align_corners=True)[0,0].numpy()
            np.save(out/f'{i:02d}-full-depth.npy',full)
            Image.fromarray(np.rint((full-full.min())/max(float(np.ptp(full)),1e-6)*255).astype(np.uint8)).save(out/f'{i:02d}-relative-depth.png')
            row['full_depth_sha256'] = digest(out/f'{i:02d}-full-depth.npy')
            row['visual_sha256'] = digest(out/f'{i:02d}-relative-depth.png')
            report['images'].append(row); write_json(out/'report.json',report)
        profile = Path(session.end_profiling())
        report['profile_file'] = profile.name; report['profile_sha256'] = digest(profile)
        report['profile_provider_events'] = dict(Counter(e.get('args',{}).get('provider') for e in json.loads(profile.read_text()) if e.get('args',{}).get('provider')))
        if set(report['profile_provider_events']) != {'DmlExecutionProvider'}: raise ValueError('Unexpected provider execution')
        report['parity_pass'] = all(r['parity']['passed'] for r in report['images'])
        report['provisional_cost_pass'] = all(r['p95_ms'] <= plan['provisional_p95_call_limit_ms'] for r in report['images'])
        report['scope'] = parent['scope']; report['visualization'] = parent['visualization']
        report['status'] = 'completed'
    except Exception as error:
        report.update(status='failed',error=repr(error),traceback=traceback.format_exc()); raise
    finally:
        write_json(out/'report.json',report)
        print(json.dumps(report,indent=2))


if __name__ == '__main__': main()
