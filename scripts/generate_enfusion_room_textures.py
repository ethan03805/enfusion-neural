"""Generate original, deterministic BCR/NMO control textures; no game assets."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def quantize(values):
    return np.floor(np.clip(values, 0, 1) * 255 + 0.5).astype(np.uint8)


def srgb(values):
    values = np.asarray(values, dtype=np.float64)
    return np.where(values <= 0.0031308, 12.92 * values, 1.055 * np.power(values, 1/2.4) - 0.055)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Choose a new empty texture-source directory')
    out.mkdir(parents=True, exist_ok=True)
    plan_path = ROOT / 'scenes/material-room-texture-control-v1.json'
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    scene_path = ROOT / plan['source_scene']
    scene = json.loads(scene_path.read_text(encoding='utf-8'))
    width, height = plan['texture_dimensions']
    if (width, height) != (512, 512):
        raise ValueError('Pattern v1 requires its declared 512x512 size')
    textures = []
    def save(name, rgba, role):
        if np.asarray(rgba).shape == (4,):
            data = np.broadcast_to(np.asarray(rgba, dtype=np.uint8), (height, width, 4)).copy()
        else:
            data = np.asarray(rgba, dtype=np.uint8)
        if data.shape != (height, width, 4):
            raise ValueError('Invalid original texture shape')
        path = out / (name + '.tif')
        Image.fromarray(data, 'RGBA').save(path, compression='tiff_lzw')
        decoded = np.asarray(Image.open(path))
        if not np.array_equal(decoded, data):
            raise ValueError('Source TIFF roundtrip changed pixels')
        textures.append({'name': name, 'file': path.name, 'sha256': digest(path), 'bytes': path.stat().st_size,
                         'pixel_sha256': hashlib.sha256(data.tobytes()).hexdigest(), 'dimensions': [width, height],
                         'role': role, 'constant_rgba8': data[0, 0].tolist() if np.all(data == data[0, 0]) else None,
                         'color_space': 'ToSRGB' if name.endswith('_BCR') else 'ToLinear'})
    for name, material in sorted(scene['materials'].items()):
        base = quantize(srgb(material['base_color_linear'])).tolist()
        save(name + '_BCR', base + [int(quantize(material['roughness']))], 'candidate original base color and roughness')
        save(name + '_NMO', [128, 128, int(quantize(material['metallic'])), 255], 'flat normal, candidate original metalness, unoccluded')
    save('metal_matte_BCR', quantize(srgb(scene['materials']['metal']['base_color_linear'])).tolist() + [217], 'metal BCR with roughness-only change to 0.85')
    save('metal_dielectric_NMO', [128, 128, 0, 255], 'metal NMO with metalness-only change to zero')
    y, x = np.indices((height, width))
    palette = np.asarray([[230, 25, 25, 153], [25, 230, 25, 153], [25, 25, 230, 153], [230, 230, 25, 153]], dtype=np.uint8)
    pattern = palette[(y % 128 >= 64).astype(int) * 2 + (x % 128 >= 64).astype(int)]
    pattern[(x % 128 < 8) | (y % 128 < 8)] = [245, 245, 245, 153]
    save('orientation_BCR', pattern, 'original asymmetric repeated color pattern; alpha roughness candidate 0.6')
    save('orientation_NMO', [128, 128, 0, 255], 'flat dielectric normal/metalness/occlusion control')
    shutil.copyfile(__file__, out / 'generator.py')
    report = {'schema_version': 1, 'operation': 'original-room-packed-texture-generation', 'status': 'succeeded',
              'generator_sha256': digest(out / 'generator.py'), 'plan_sha256': digest(plan_path), 'plan': plan,
              'source_scene_sha256': digest(scene_path), 'textures': textures,
              'native_import_verified': False, 'rendered_response_verified': False}
    (out / 'textures.json').write_bytes((json.dumps(report, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'status': 'succeeded', 'textures': len(textures), 'dimensions': [width, height]}))


if __name__ == '__main__':
    main()
