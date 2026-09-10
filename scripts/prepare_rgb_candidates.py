"""Download pinned public author sources and hash-verified RGB candidate weights.

These research candidates are not part of the working playable package.
"""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    'regen': {
        'repository': 'stefanos50/REGEN',
        'revision': 'de240056522d066235b48b541e7d49f28c80f1ed',
        'files': ['LICENSE', 'README.md', 'onnx_utils/generator.py', 'onnx_utils/regen_onnx_eport.py',
                  'onnx_utils/test_onnx.py', 'code/models/networks.py', 'code/options/base_options.py'],
        'checkpoint': 'gta2cityscapes.pth',
        'checkpoint_sha256': '46258537fb99b04c9bc891691361f38c59f3fdff79ee9f495e69402aa58c6a69',
        'drive_id': '18FpCT8x7eEangLio2cx_2C_M9wW7W2Hz',
        'author_checkpoint_folder': 'https://drive.google.com/drive/folders/19Q8E9wy3MR-vUfOfVwytIzv4QNpndYo0'
    },
    'deeplpf': {
        'repository': 'sjmoran/deeplpf-image-enhancement',
        'revision': 'b6d6764b548667f51eda2f1a6aafd484822de3ec',
        'files': ['LICENSE', 'README.md', 'model.py', 'unet.py', 'util.py', 'data.py', 'main.py', 'metric.py'],
        'checkpoint': 'adobe-dpe.pt',
        'checkpoint_sha256': 'e23781cded4ee64177e4ff82f61dc562cf5f524e4e13dc32aa0175cb6f38c69b',
        'checkpoint_path': 'pretrained_models/adobe_dpe/deeplpf_validpsnr_23.378_validloss_0.033_testpsnr_23.904_testloss_0.031_epoch_424_model.pt'
    }
}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def download(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    # Interrupted files are retained, never mistaken for a complete download.
    partial = path.with_name(path.name+'.partial')
    if partial.exists():
        raise FileExistsError('Inspect retained partial download: '+str(partial))
    urllib.request.urlretrieve(url, partial)
    partial.rename(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=MODELS, required=True)
    args = parser.parse_args()
    spec = MODELS[args.model]
    root = ROOT/'runs/pretrained'/args.model
    base = f"https://raw.githubusercontent.com/{spec['repository']}/{spec['revision']}/"
    for name in spec['files']:
        download(base+name, root/name)
    checkpoint = root/spec['checkpoint']
    if not checkpoint.exists():
        if 'drive_id' in spec:
            import gdown
            partial = checkpoint.with_name(checkpoint.name+'.partial')
            if partial.exists():
                raise FileExistsError('Inspect retained partial download: '+str(partial))
            result = gdown.download(id=spec['drive_id'], output=str(partial), use_cookies=False, quiet=False)
            if result is None:
                raise RuntimeError('Public author checkpoint download failed')
            if sha(partial) != spec['checkpoint_sha256']:
                raise ValueError('Downloaded checkpoint differs; partial file retained')
            partial.rename(checkpoint)
        else:
            download(base+spec['checkpoint_path'], checkpoint)
    if sha(checkpoint) != spec['checkpoint_sha256']:
        raise ValueError('Checkpoint hash mismatch; existing file retained')
    # Compare source with measured evidence if present, so a modified local file
    # cannot silently be relabeled as the pinned author implementation.
    evidence = ROOT/f'evidence/{args.model}-evaluation-v1.json'
    source_hashes = {name: sha(root/name) for name in spec['files']}
    if evidence.exists():
        expected = json.loads(evidence.read_text())['measurement']['source_hashes']
        for name, digest in expected.items():
            if source_hashes.get(name) != digest:
                raise ValueError('Author source differs from measured input: '+name)
    record = dict(spec, source_hashes=source_hashes, checkpoint_bytes=checkpoint.stat().st_size)
    (root/'source-pinned.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
