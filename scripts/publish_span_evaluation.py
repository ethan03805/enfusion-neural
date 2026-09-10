"""Publish measured restoration evidence and four reviewed street controls."""
import json
from pathlib import Path
import shutil
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    target = ROOT / 'evidence/span-evaluation-v1.json'
    if target.exists(): raise FileExistsError('Evidence already published')
    fp = ROOT / 'runs/span-evaluation-v1'; half = ROOT / 'runs/span-half-v2'
    failed = ROOT / 'runs/span-half-v1'; residual = ROOT / 'runs/span-residual-v1'
    full = read(fp / 'report.json'); small = read(half / 'report.json'); bad = read(failed / 'report.json')
    transfer = read(residual / 'report.json')
    if small['parent_report_sha256'] != digest(fp / 'report.json') or transfer['parent_report_sha256'] != digest(fp / 'report.json'):
        raise ValueError('Parent evaluation changed')
    for directory, report in [(fp, full), (half, small)]:
        if report['status'] != 'completed' or not report['cpu_dml_parity']['passed'] or report['provisional_cost_gate']:
            raise ValueError('Expected completed, numerically valid, over-budget result')
        if digest(directory / 'model.onnx') != report['onnx_sha256'] or report['profile_provider_events'] != {'DmlExecutionProvider': 43}:
            raise ValueError('Graph/provider evidence changed')
        for i, row in enumerate(report['images']):
            if digest(ROOT / row['source']) != row['source_sha256'] or digest(directory / f'{i:02d}-raw.npy') != row['raw_sha256']:
                raise ValueError('Image input or output changed')
    if bad['status'] != 'failed' or 'topologically sorted' not in bad['error'] or digest(failed / 'driver.py') != bad['driver_sha256']:
        raise ValueError('Initial conversion failure changed')
    for name, report in [('evaluate_span.py', full), ('evaluate_span_half.py', small), ('diagnose_span_residual.py', transfer)]:
        if digest(ROOT / 'scripts' / name) != report['driver_sha256']: raise ValueError('Evaluation driver changed')
    for i, row in enumerate(transfer['images']):
        if digest(residual / f'{i:02d}-protected.png') != row['png_sha256']: raise ValueError('Residual output changed')
    files = [(fp / '03-original.png', 'span-street-original.png', 'Original 1440p RGB control; lossless decoded PNG'),
        (fp / '03-bicubic.png', 'span-street-bicubic.png', 'Pillow bicubic downsample to 1280x720, then bicubic upsample to 2560x1440'),
        (fp / '03-raw.png', 'span-street-raw.png', 'Same 1280x720 input through SPAN x2 FP32; round and clip output to RGB8; no extra resize'),
        (residual / '03-protected.png', 'span-street-protected.png', 'Original plus bounded half-strength SPAN-minus-bicubic residual; round and clip RGB8; no resize')]
    records = [fp / 'report.json', half / 'report.json', failed / 'report.json', failed / 'driver.py',
        residual / 'report.json', residual / 'parameters-before-composition.json',
        fp / full['profile_file'], half / small['profile_file'], ROOT / 'scenes/playable-rgb-restoration-v1.json']
    report = {'schema_version': 1, 'date': '2026-09-10', 'outcome': 'restoration_improves_bicubic_but_live_integration_rejected',
        'measurement': full, 'half_precision': small, 'conversion_failure': bad, 'source_composition': transfer,
        'review': {'scope': 'All four original and FP32 model images, all four residual compositions, and the street bicubic control inspected at native 2560x1440.',
            'raw': 'More roof-line and facade detail than bicubic; original captures retain finer grass, road and foliage detail. Scene colors, broad openings and cover remain recognizable. Some small details stay softened. This is not semantic or motion acceptance.',
            'residual': 'Small sharpening of roof lines, road and foliage. No demonstrated material-response or illumination improvement. Protected luminance/HUD pixels are exact, but unprotected color channels introduce a small amount of clipping, retained in metrics.',
            'decision': 'Both precision variants exceed the 20ms provisional call budget, and the residual is insufficient appearance gain. No motion or live replacement test is justified for this graph.',
            'unknown': 'Peak GPU memory, GPU-only time, motion stability, complete application performance and any photorealistic gain are unmeasured.'},
        'source_hashes': {p.relative_to(ROOT).as_posix(): digest(p) for p in records},
        'published_media': [{'file': name, 'sha256': digest(path), 'transformation': transform} for path, name, transform in files],
        'working_package_changed': False, 'new_training_performed': False,
        'next': 'Preserve the working live pipeline. The next appearance test must target lighting/material response using verifiable scene information; do not treat further synthetic-resolution gains as completion of photorealism.'}
    write_json(target, report)
    manifest_path = ROOT / 'docs/media/manifest.json'; manifest = read(manifest_path)
    for path, name, transform in files:
        destination = ROOT / 'docs/media' / name
        if destination.exists(): raise FileExistsError(name)
        if Image.open(path).size != (2560, 1440): raise ValueError('Unexpected image size')
        shutil.copyfile(path, destination)
        manifest['images'].append({'file': name, 'sha256': digest(destination), 'bytes': destination.stat().st_size,
            'dimensions': [2560, 1440], 'source_record': target.relative_to(ROOT).as_posix(),
            'source_artifact': path.relative_to(ROOT).as_posix(), 'source_sha256': digest(path),
            'transformation': transform, 'rights': 'Arma Reforger imagery © Bohemia Interactive, outside MIT license; SPAN author project Apache-2.0'})
    write_json(manifest_path, manifest)
    print('Published both precision measurements, failed conversion, residual limits and four reviewed street images.')


if __name__ == '__main__': main()
