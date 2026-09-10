"""Evaluate pinned SPAN restoration against originals and bicubic controls."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import types

import numpy as np
from PIL import Image
import onnxruntime as ort
from skimage.metrics import structural_similarity
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json
from prepare_span import CHECKPOINT_SHA


def tensor(image):
    return np.ascontiguousarray((np.asarray(image, dtype=np.float32) / 255).transpose(2, 0, 1)[None])


def save(value, path):
    pixels = np.rint(value[0].transpose(1, 2, 0).clip(0, 1) * 255).astype(np.uint8)
    Image.fromarray(pixels).save(path)


def metrics(value, target):
    value = value.clip(0, 1)[0, :, 8:-8, 8:-8]; target = target[0, :, 8:-8, 8:-8]
    mse = float(np.mean((value-target)**2, dtype=np.float64))
    return {'rgb_psnr_db': float(-10*np.log10(mse)),
        'ssim': float(structural_similarity(target.transpose(1, 2, 0), value.transpose(1, 2, 0), data_range=1., channel_axis=2)),
        'mean_abs': float(np.abs(value-target).mean())}


def load_author(source):
    spec = json.loads((source / 'source-pinned.json').read_text())
    for file, expected in spec['source_hashes'].items():
        if digest(source / file) != expected: raise ValueError('Changed author source')
    if digest(source / 'spanx2_ch48.pth') != CHECKPOINT_SHA: raise ValueError('Changed checkpoint')
    code = (source / 'span_arch.py').read_text()
    for registration in ['from basicsr.utils.registry import ARCH_REGISTRY\n', '@ARCH_REGISTRY.register()\n']:
        if code.count(registration) != 1: raise ValueError('Unexpected registry decoration')
        code = code.replace(registration, '')
    author = types.ModuleType('span_author')
    exec(compile(code, str(source / 'span_arch.py'), 'exec'), author.__dict__)
    model = author.SPAN(3, 3, feature_channels=48, upscale=2).eval()
    state = torch.load(source / 'spanx2_ch48.pth', map_location='cpu', weights_only=True)
    model.load_state_dict(state['params_ema'], strict=True)
    return author, model, spec


def fuse(module, author):
    for name, child in list(module.named_children()):
        if isinstance(child, author.Conv3XC):
            child.update_params()
            setattr(module, name, child.eval_conv)
        else: fuse(child, author)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); out = a.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    plan_file = ROOT / 'scenes/playable-rgb-restoration-v1.json'; plan = json.loads(plan_file.read_text())
    source = ROOT / 'runs/pretrained/span-source-v1'
    adapters = [json.loads(s) for s in subprocess.check_output([str(ROOT / 'build/Release/enr_adapter_info.exe')], text=True).splitlines()]
    adapter = next(v for v in adapters if v['description'] == 'AMD Radeon RX 7800 XT' and not v['software'])
    report = {'schema_version': 1, 'status': 'started', 'plan': plan, 'plan_sha256': digest(plan_file),
        'driver_sha256': digest(Path(__file__)), 'precision': 'FP32', 'adapter': adapter,
        'runtime': ort.__version__, 'torch': torch.__version__, 'input_dimensions': [1280, 720],
        'output_dimensions': [2560, 1440], 'images': [],
        'timing_scope': 'Synchronized ONNX Runtime call with CPU input upload and output readback; game stopped. Excludes setup, image I/O, resizing and metrics. Not pure GPU time or application FPS.'}
    write_json(out / 'report.json', report)
    try:
        torch.set_num_threads(4)
        author, model, pinned = load_author(source); report['source'] = pinned
        report['checkpoint_parameters'] = sum(p.numel() for p in model.parameters())
        originals = [Image.open(ROOT / path).convert('RGB') for path in plan['inputs']]
        if any(im.size != (2560, 1440) for im in originals): raise ValueError('Expected native 1440p controls')
        small = [im.resize((1280, 720), Image.Resampling.BICUBIC) for im in originals]
        inputs = [tensor(im) for im in small]
        x = torch.from_numpy(inputs[0])
        with torch.inference_mode():
            began = time.perf_counter(); original_reference = model(x).numpy().copy()
            report['author_cpu_ms'] = (time.perf_counter()-began)*1000
            print('Author CPU reference', report['author_cpu_ms'], 'ms', flush=True)
            fuse(model, author)
            reference = model(x).numpy().copy()
            delta = np.abs(reference-original_reference)
            report['fusion_parity'] = {'max_abs': float(delta.max()), 'mean_abs': float(delta.mean()), 'passed': bool(delta.max() <= .0001)}
            if not report['fusion_parity']['passed']: raise ValueError('One-time fusion differs')
            report['inference_parameters'] = sum(p.numel() for p in model.parameters())
            np.save(out / 'cpu-reference.npy', original_reference)
            torch.onnx.export(model, x, str(out / 'model.onnx'), opset_version=17, input_names=['input'],
                              output_names=['output'], dynamo=False, do_constant_folding=True)
        del model
        report['onnx_sha256'] = digest(out / 'model.onnx')
        options = ort.SessionOptions(); options.enable_mem_pattern = False; options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.enable_profiling = True; options.profile_file_prefix = str(out / 'ort-profile')
        options.add_session_config_entry('session.disable_cpu_ep_fallback', '1')
        began = time.perf_counter()
        session = ort.InferenceSession(str(out / 'model.onnx'), sess_options=options,
            providers=[('DmlExecutionProvider', {'device_id': str(adapter['index'])})])
        session.disable_fallback(); report['session_setup_ms'] = (time.perf_counter()-began)*1000
        report['providers'] = session.get_providers()
        for i, (x, original, low) in enumerate(zip(inputs, originals, small)):
            for _ in range(5 if i == 0 else 1): output = session.run(['output'], {'input': x})[0]
            timings = []
            for _ in range(20 if i == 0 else 5):
                began = time.perf_counter(); output = session.run(['output'], {'input': x})[0]
                timings.append((time.perf_counter()-began)*1000)
            if not np.isfinite(output).all(): raise ValueError('Nonfinite output')
            target = tensor(original); bicubic = tensor(low.resize(original.size, Image.Resampling.BICUBIC))
            np.save(out / f'{i:02d}-raw.npy', output)
            save(output, out / f'{i:02d}-raw.png'); save(target, out / f'{i:02d}-original.png')
            save(bicubic, out / f'{i:02d}-bicubic.png'); low.save(out / f'{i:02d}-input.png')
            item = {'source': plan['inputs'][i], 'source_sha256': digest(ROOT / plan['inputs'][i]),
                'timings_ms': timings, 'median_ms': float(np.median(timings)), 'p95_ms': float(np.percentile(timings, 95)),
                'raw_range': [float(output.min()), float(output.max())],
                'raw_out_of_range_channel_fraction': float(np.mean((output < 0) | (output > 1))),
                'model': metrics(output, target), 'bicubic': metrics(bicubic, target), 'raw_sha256': digest(out / f'{i:02d}-raw.npy')}
            item['psnr_gain_db'] = item['model']['rgb_psnr_db'] - item['bicubic']['rgb_psnr_db']
            if i == 0:
                delta = np.abs(output-original_reference)
                report['cpu_dml_parity'] = {'max_abs': float(delta.max()), 'mean_abs': float(delta.mean()),
                    'passed': bool(delta.max() <= .001 and delta.mean() <= .0001)}
            report['images'].append(item); write_json(out / 'report.json', report)
            print(json.dumps(item), flush=True)
        profile = Path(session.end_profiling()); report['profile_file'] = profile.name
        counts = {}
        for e in json.loads(profile.read_text()):
            provider = e.get('args', {}).get('provider')
            if provider: counts[provider] = counts.get(provider, 0)+1
        report['profile_provider_events'] = counts
        if counts.get('CPUExecutionProvider', 0) or not counts.get('DmlExecutionProvider', 0): raise ValueError('Unexpected provider assignment')
        if not report['cpu_dml_parity']['passed']: raise ValueError('CPU/DirectML parity failed')
        report['restoration_numeric_gate'] = sum(v['psnr_gain_db'] >= .2 for v in report['images']) >= 3 and report['images'][3]['psnr_gain_db'] >= .2
        report['provisional_cost_gate'] = report['images'][0]['p95_ms'] <= 20
        report['visual_review'] = 'Pending full-image inspection; numerical completion is not appearance acceptance.'
        report['status'] = 'completed'
    except Exception as error:
        report.update(status='failed', error=repr(error)); raise
    finally: write_json(out / 'report.json', report)


if __name__ == '__main__': main()
