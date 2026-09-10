"""Reproduce the selected author SPAN files; other archive contents stay compressed."""
import json
from pathlib import Path
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json

REVISION = 'c77a5917759f09e66fbc7124220c5afc5ee221e5'
CHECKPOINT_SHA = '561fd5cf419a23d4de1231ce258180f61aee4aa8caa1aaaa783769c7301847bc'
ARCHIVE_SHA = '675b653c5e730e149bb75864e04e4f3440fe8eb46e1c6f44d21b973fb5f747dc'
FILES = {'basicsr/archs/span_arch.py': 'span_arch.py', 'README.md': 'README.md',
         'LICENSE.txt': 'LICENSE.txt', 'LICENSE/README.md': 'LICENSE-README.md'}


def main():
    out = ROOT / 'runs/pretrained/span-source-v1'; out.mkdir(parents=True, exist_ok=True)
    base = 'https://raw.githubusercontent.com/hongyuanyu/SPAN/' + REVISION + '/'
    for remote, local in FILES.items():
        data = urllib.request.urlopen(base + remote, timeout=30).read(200000)
        path = out / local
        if path.exists() and path.read_bytes() != data: raise ValueError('Local source changed: ' + local)
        path.write_bytes(data)
    archive = out / 'span.zip'
    if not archive.exists():
        import gdown
        partial = out / 'span.zip.partial'
        if partial.exists(): raise FileExistsError('Retained partial archive needs inspection')
        if not gdown.download(id='1iYUA2TzKuxI0vzmA-UXr_nB43XgPOXUg', output=str(partial), use_cookies=False):
            raise ValueError('Author download failed')
        if digest(partial) != ARCHIVE_SHA: raise ValueError('Archive hash differs')
        partial.rename(archive)
    if digest(archive) != ARCHIVE_SHA: raise ValueError('Archive changed')
    with zipfile.ZipFile(archive) as z:
        data = z.read('spanx2_ch48.pth')
    checkpoint = out / 'spanx2_ch48.pth'
    if checkpoint.exists() and checkpoint.read_bytes() != data: raise ValueError('Checkpoint changed')
    checkpoint.write_bytes(data)
    if digest(checkpoint) != CHECKPOINT_SHA: raise ValueError('Checkpoint hash differs')
    report = {'repository': 'https://github.com/hongyuanyu/SPAN', 'revision': REVISION,
        'archive_url': 'https://drive.google.com/file/d/1iYUA2TzKuxI0vzmA-UXr_nB43XgPOXUg/view',
        'archive_bytes': archive.stat().st_size, 'archive_sha256': ARCHIVE_SHA,
        'checkpoint': checkpoint.name, 'checkpoint_bytes': checkpoint.stat().st_size,
        'checkpoint_sha256': CHECKPOINT_SHA, 'state': 'params_ema', 'license': 'Apache-2.0 author project',
        'source_hashes': {local: digest(out / local) for local in FILES.values()}}
    write_json(out / 'source-pinned.json', report)
    print(json.dumps(report))


if __name__ == '__main__': main()
