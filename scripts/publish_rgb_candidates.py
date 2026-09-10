"""Retain the reviewed raw RGB candidate evidence and exact comparison images."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest_path = ROOT/'docs/media/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    models = [
        ('regen', 'de240056522d066235b48b541e7d49f28c80f1ed',
         'https://github.com/stefanos50/REGEN', 'BSD notices retained in author LICENSE',
         ['Road/sign: sky develops coarse mottled texture; fine flowers and sign edge soften.',
          'Facade: orange roof becomes green/gray; blue pole loses saturation; sky develops texture.',
          'Foliage: fine leaves soften, bright sky gaps develop blotches and HUD text degrades.'],
         'Reject raw live integration: altered material identity and texture artifacts, plus 53–54 ms synchronized processing at only 960x544. CPU/DirectML parity passes, so this is not a backend conversion failure.'),
        ('deeplpf', 'b6d6764b548667f51eda2f1a6aafd484822de3ec',
         'https://github.com/sjmoran/deeplpf-image-enhancement', 'BSD-3-Clause',
         ['Road/sign: stronger contrast and saturation; shadow foliage is driven to black.',
          'Facade: roof color retained, but dark doorway and window contrast decrease.',
          'Foliage: darker, more saturated rendering; fine shaded foliage becomes harder to distinguish.'],
         'Raw output rejected as default because of visibility loss. The source-protected diagnostic avoids new black clipping but remains a color/contrast change without substantial material or lighting improvement. Close this integration attempt; no GPU or temporal acceptance.')]
    for slug, revision, url, license_name, reviews, decision in models:
        run = ROOT/f'runs/{slug}-evaluation-v1'
        report = json.loads((run/'report.json').read_text())
        record_path = ROOT/f'evidence/{slug}-evaluation-v1.json'
        record = {'schema_version': 1, 'candidate': report['candidate'], 'author': url,
                  'author_revision': revision, 'license': license_name,
                  'raw_report_sha256': sha(run/'report.json'), 'measurement': report,
                  'review': reviews, 'decision': decision, 'published_media': [],
                  'limitations': 'Three selected single frames; no aligned photographic ground truth, temporal acceptance or live-game timing. Raw evaluation inputs/outputs are 960x544. The separately labeled DeepLPF source-protected pair is an offline 1440p transfer, not live neural output.'}
        provenance = ROOT/f'runs/pretrained/{slug}/source-pinned.json'
        if provenance.exists(): record['provenance'] = json.loads(provenance.read_text())
        for index in range(3):
            source = run/f'{index:02d}-source-input.png'
            # REGEN writes its normalized float input back to PNG with truncation;
            # retain each candidate's exact input instead of implying byte equality.
            for kind, path in [('source', source), ('raw', run/f'{index:02d}-raw-model.png')]:
                name = f'{slug}-{index:02d}-{kind}.png'
                entry = {'file': name, 'source_record': str(record_path.relative_to(ROOT)).replace('\\', '/'),
                         'source_artifact': str(path.relative_to(ROOT)).replace('\\', '/'),
                         'sha256': sha(path), 'bytes': path.stat().st_size, 'dimensions': [960, 544],
                         'transformation': 'Exact evaluation PNG copied without further scaling or editing. Original 2560x1440 gameplay frame was resized bilinearly to 960x544 before inference. Raw model output is labeled and unbounded.',
                         'rights': 'Arma Reforger imagery © Bohemia Interactive; outside MIT code license'}
                shutil.copyfile(path, ROOT/'docs/media'/name)
                manifest['images'] = [x for x in manifest['images'] if x['file'] != name]
                manifest['images'].append(entry)
                record['published_media'].append(entry)
        if slug == 'deeplpf':
            transfer_path = ROOT/'runs/deeplpf-transfer-v1/report.json'
            record['source_protected_diagnostic'] = json.loads(transfer_path.read_text())
            record['source_protected_review'] = 'All three full-resolution outputs inspected. Roof, openings, bark and fences retain source detail; sunlight/grass gain color and contrast. No new black clipping, but no substantial reconstruction or lighting gain. No motion review or native integration warranted for this appearance objective.'
            # One representative exact 1440p pair on the concise candidate page.
            paths = [('source', ROOT/report['images'][1]['source']), ('protected', ROOT/'runs/deeplpf-transfer-v1/01-protected.png')]
            for kind, path in paths:
                name = f'deeplpf-facade-{kind}.png'
                entry = {'file': name, 'source_record': str(record_path.relative_to(ROOT)).replace('\\', '/'),
                         'source_artifact': str(path.relative_to(ROOT)).replace('\\', '/'),
                         'sha256': sha(path), 'bytes': path.stat().st_size, 'dimensions': [2560, 1440],
                         'transformation': 'Exact full-resolution source or offline protected-transfer PNG copied without scaling. The model predicted at 960x544; a smoothed bounded RGB gain is applied to original pixels with source-shadow, highlight and fixed HUD protection. Not live output.',
                         'rights': 'Arma Reforger imagery © Bohemia Interactive; outside MIT code license'}
                shutil.copyfile(path, ROOT/'docs/media'/name)
                manifest['images'] = [x for x in manifest['images'] if x['file'] != name]
                manifest['images'].append(entry)
                record['published_media'].append(entry)
        (record_path).write_text(json.dumps(record, indent=2), encoding='utf-8')
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
