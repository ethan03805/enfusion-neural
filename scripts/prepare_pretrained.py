"""Download pinned author checkpoints, verify bytes, export native research formats."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

MODELS = {
    'zero-dce-plusplus': {
        'repository': 'Li-Chongyi/Zero-DCE_extension',
        'revision': '09f202b690f82da939b8e6ec8535960ae97ad8bd',
        'terms': 'Author academic research / CC BY-NC 4.0; separate from MIT code',
        'files': {
            'Epoch99.pth': ('Zero-DCE++/snapshots_Zero_DCE++/Epoch99.pth', 'ca8855b90df9a80fa4195a831f33d3476b1964f787eb70602797c773067f3b84'),
            'model.py': ('Zero-DCE++/model.py', '508ad1b0eece0b2a99503ba8b4461a9695b79ecf1b30b046be16f7aaa99c20e3'),
            'README.md': ('README.md', '0e18a0584cf4ddc92bd16045f226b3c6f99cc623ff96ff931c3236b234f1faa3'),
        },
    },
    'adaptive-3dlut': {
        'repository': 'HuiZeng/Image-Adaptive-3DLUT',
        'revision': 'b491f6df64a588864739a157db271e5c848e1805',
        'terms': 'Apache-2.0; retain author LICENSE and attribution',
        'files': {
            'classifier.pth': ('pretrained_models/sRGB/classifier.pth', 'bae9865395625ecae58cfe86147e521093bb1e29e7b2544e02adb238b8035021'),
            'LUTs.pth': ('pretrained_models/sRGB/LUTs.pth', 'c1bb2bc4b7239c1a7e96159f5923123ba796b1fceb0b8c3132b423ea825b821a'),
            'models.py': ('models.py', '3f39c49aebd2b85787638bc9d402d21d5d664b844edd5fb8d5e4ce1fdb1d9f3f'),
            'LICENSE': ('LICENSE', 'c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4'),
            'README.md': ('README.md', '45cd2cc7d86bd7f45649308b508fd1e42b5061e15d89d0ca9980e72656dd8956'),
        },
    },
}


def download(kind, folder):
    spec = MODELS[kind]
    folder.mkdir(parents=True, exist_ok=True)
    report = {k:v for k,v in spec.items() if k!='files'}
    report['files'] = []
    for name, (relative, expected) in spec['files'].items():
        url = 'https://raw.githubusercontent.com/{}/{}/{}'.format(spec['repository'], spec['revision'], relative)
        file = folder/name
        data = file.read_bytes() if file.exists() else urllib.request.urlopen(url, timeout=30).read()
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected: raise ValueError('Checkpoint/source hash mismatch: '+name)
        if not file.exists(): file.write_bytes(data)
        report['files'].append({'file': name, 'url': url, 'sha256': actual, 'bytes': len(data)})
    (folder/'source-pinned.json').write_text(json.dumps(report, indent=2))
    return report


def export(kind, folder):
    import numpy as np
    import torch
    torch.set_num_threads(1)
    parts = []
    if kind == 'zero-dce-plusplus':
        state = torch.load(folder/'Epoch99.pth', map_location='cpu', weights_only=True)
        for i in range(1,8):
            for layer in ['depth_conv', 'point_conv']:
                for term in ['weight','bias']:
                    parts.append(state[f'e_conv{i}.{layer}.{term}'].numpy().astype('<f4').tobytes())
        data = b'ZDC1'+b''.join(parts)
    else:
        state = torch.load(folder/'classifier.pth', map_location='cpu', weights_only=True)
        for i in [1,4,7,10,13,16]:
            for term in ['weight','bias']:
                parts.append(state[f'model.{i}.{term}'].numpy().astype('<f4').tobytes())
            if i<13:
                for term in ['weight','bias']:
                    parts.append(state[f'model.{i+2}.{term}'].numpy().astype('<f4').tobytes())
        luts = torch.load(folder/'LUTs.pth', map_location='cpu', weights_only=True)
        for i in range(3):
            lut = luts[str(i)]['LUT'].numpy()
            if lut.shape != (3,33,33,33): raise ValueError('Unexpected LUT shape')
            parts.append(lut.astype('<f4').tobytes())
        data = b'LUT1'+b''.join(parts)
    file = folder/'weights.bin'
    if file.exists() and file.read_bytes()!=data: raise ValueError('Refusing to replace different exported weights')
    file.write_bytes(data)
    report = {'format': data[:4].decode(), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'precision': 'FP32 little-endian', 'source': 'source-pinned.json', 'modified': 'Author checkpoint tensors serialized into documented native layout; model parameters unchanged'}
    (folder/'export.json').write_text(json.dumps(report, indent=2))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model', choices=MODELS, required=True)
    p.add_argument('--root', type=Path, default=Path('runs/pretrained'))
    p.add_argument('--download-only', action='store_true')
    a = p.parse_args(); folder = a.root/a.model
    download(a.model, folder)
    if not a.download_only: print(json.dumps(export(a.model, folder), indent=2))


if __name__ == '__main__': main()
