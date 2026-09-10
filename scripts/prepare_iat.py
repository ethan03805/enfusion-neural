"""Retain pinned IAT author source and its exposure-correction checkpoint."""
import json
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json

REPOSITORY = 'cuiziteng/Illumination-Adaptive-Transformer'
REVISION = 'c76472265247f47cea57649af28b15018bb64cb1'
FILES = ['LICENSE', 'README.md', 'IAT_enhance/readme.md', 'IAT_enhance/img_demo.py',
         'IAT_enhance/evaluation_exposure.py', 'IAT_enhance/model/IAT_main.py',
         'IAT_enhance/model/blocks.py', 'IAT_enhance/model/global_net.py',
         'IAT_enhance/best_Epoch_exposure.pth']


def main():
    out = ROOT / 'runs/pretrained/iat-exposure-v1'
    existing = json.loads((out / 'source.json').read_text()) if (out / 'source.json').exists() else None
    for name in FILES:
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            partial = path.with_name(path.name + '.partial')
            if partial.exists():
                raise FileExistsError('Inspect interrupted download: ' + str(partial))
            urllib.request.urlretrieve(f'https://raw.githubusercontent.com/{REPOSITORY}/{REVISION}/{name}', partial)
            partial.rename(path)
        if existing and digest(path) != existing['files'][name]['sha256']:
            raise ValueError('Changed retained author artifact: ' + name)
    record = {'repository': REPOSITORY, 'revision': REVISION,
        'checkpoint': 'IAT_enhance/best_Epoch_exposure.pth',
        'files': {name: {'sha256': digest(out / name), 'bytes': (out / name).stat().st_size,
                       'url': f'https://raw.githubusercontent.com/{REPOSITORY}/{REVISION}/{name}'} for name in FILES}}
    evidence = ROOT / 'evidence/iat-evaluation-v1.json'
    if evidence.exists() and record != json.loads(evidence.read_text())['source']:
        raise ValueError('Pinned author artifacts differ from measured evidence')
    write_json(out / 'source.json', record)
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
