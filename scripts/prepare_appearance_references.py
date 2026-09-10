"""Retain a bounded CC0 material reference set, not paired Reforger ground truth."""
import hashlib
import json
from pathlib import Path
import urllib.request
import urllib.error

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = {
    'asphalt_02': 'Town road: aggregate and matte response. Not the same cracks, road markings, UVs or wear as the game.',
    'roof_tiles': 'Town orange roof: terracotta surface variation. Tile shape and arrangement differ; not an identity-preserving replacement texture.',
    'bark_brown_01': 'Foliage view trunk: furrowed bark response. Tree species and groove placement are not matched.'
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url, path):
    if not path.exists():
        partial = path.with_name(path.name+'.partial')
        if partial.exists(): raise FileExistsError('Inspect partial download: '+str(partial))
        urllib.request.urlretrieve(url, partial)
        partial.rename(path)


def main():
    root = ROOT/'runs/reference-assets-v1'
    root.mkdir(parents=True, exist_ok=True)
    license_url = 'https://polyhaven.com/license'
    try:
        fetch(license_url, root/'polyhaven-license.html')
        license_fetch = {'status': 'downloaded', 'sha256': sha(root/'polyhaven-license.html')}
    except urllib.error.HTTPError as error:
        # The public license page was read through the web tool. A direct
        # automated HTML request can be refused while the documented API works.
        license_fetch = {'status': 'unavailable', 'error': str(error),
                         'verification': 'Primary https://polyhaven.com/license page read via web tool on 2026-09-10: all assets are CC0.'}
        (root/'license-download-failure.json').write_text(json.dumps(license_fetch, indent=2))
    report = {'schema_version': 1, 'license': 'CC0', 'license_url': license_url,
              'license_page_fetch': license_fetch,
              'scope': 'Three category-level PBR appearance references for road, roof and bark. No game asset was replaced, no paired ground truth produced and no training performed.',
              'visual_review': 'All three diffuse maps inspected at 1024x1024: asphalt aggregate/cracks, orange terracotta tiles with mossy wear, and deeply furrowed brown bark. Their local patterns differ from the game. Suitable material-category references; not matched asset identity or aligned training targets.',
              'assets': []}
    for name, applicability in ASSETS.items():
        for endpoint in ['info', 'files']:
            fetch(f'https://api.polyhaven.com/{endpoint}/{name}', root/f'{name}-{endpoint}.json')
        info = json.loads((root/f'{name}-info.json').read_text())
        files = json.loads((root/f'{name}-files.json').read_text())
        item = {'id': name, 'source': f'https://polyhaven.com/a/{name}', 'authors': info['authors'],
                'category': info.get('category'), 'dimensions_mm': info.get('dimensions'),
                'applicability': applicability, 'maps': [],
                'metadata_sha256': {kind: sha(root/f'{name}-{kind}.json') for kind in ['info', 'files']}}
        for channel in ['Diffuse', 'Rough', 'nor_dx']:
            data = files[channel]['1k']['png']
            path = root/data['url'].rsplit('/', 1)[1]
            fetch(data['url'], path)
            if path.stat().st_size != data['size'] or hashlib.md5(path.read_bytes()).hexdigest() != data['md5']:
                raise ValueError('Reference differs from author metadata: '+path.name)
            with Image.open(path) as im:
                dimensions = list(im.size)
                im.verify()
            item['maps'].append({'channel': channel, 'url': data['url'], 'local_file': path.name,
                                 'bytes': path.stat().st_size, 'sha256': sha(path), 'author_md5': data['md5'],
                                 'dimensions': dimensions, 'modified': False})
        report['assets'].append(item)
    (ROOT/'evidence/playable-appearance-references-v1.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'assets': list(ASSETS), 'bytes': sum(m['bytes'] for a in report['assets'] for m in a['maps']), 'scope': report['scope']}, indent=2))


if __name__ == '__main__':
    main()
