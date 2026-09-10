"""Publish the specifically reviewed live pair and rejected photographic candidate."""
import csv
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values):
    return dict(zip(['min','p50','p95','p99','max'], map(float,np.percentile(values,[0,50,95,99,100]))))


def main():
    run = ROOT/'runs/companion-hwnd-v1'
    with (run/'frames.csv').open() as f: native = sorted(csv.DictReader(f),key=lambda r:float(r['present_call_qpc_ms']))
    with (run/'presentmon.csv').open(encoding='utf-8-sig') as f: pm = [r for r in csv.DictReader(f) if r['Application']=='enr_companion.exe' and r['Dropped']=='0']
    times = np.array([float(r['present_call_qpc_ms']) for r in native])
    joined = []
    for r in pm:
        present = float(r['QPCTime'])*1000
        i = int(np.argmin(abs(times-present)))
        residual = abs(times[i]-present)
        if residual<=1:
            joined.append({'frame':int(native[i]['frame']),'present_qpc_ms':present,'residual_ms':float(residual),'capture_to_display_ms':present+float(r['msUntilDisplayed'])-float(native[i]['capture_qpc_ms'])})
    record = {'schema_version':1,'date':'2026-09-10','run':'companion-hwnd-v1','configuration_scope':'Early first-person loop sample using engine defaults; not the corrected standard/reduced comparison','run_manifest':json.loads((run/'run.json').read_text()),'source_hashes':{f.name:sha(f) for f in run.iterdir() if f.is_file()},'gpu_copy_inference_draw_ms':percentile([float(r['gpu_copy_draw_ms']) for r in native if float(r['gpu_copy_draw_ms'])>=0]),'latency':{'scope':'WGC compositor frame timestamp to PresentMon reported display. Excludes keyboard/mouse sampling and physical display response. PresentMon v1 QPCTime is seconds despite --qpc_time_ms.','eligible_frames':len(pm),'joined_frames':len(joined),'join_tolerance_ms':1,'latency_ms':percentile([r['capture_to_display_ms'] for r in joined]),'joins':joined},'zero_dce':json.loads((ROOT/'runs/pretrained/zero-dce-plusplus/source-pinned.json').read_text()),'zero_dce_native_parity':json.loads((ROOT/'runs/pretrained/zero-dce-plusplus/native-parity.json').read_text()),'adaptive_lut':json.loads((ROOT/'runs/pretrained/adaptive-3dlut/source-pinned.json').read_text()),'adaptive_lut_cpu_evaluation':json.loads((ROOT/'runs/adaptive-lut-evaluation-v1/evaluation.json').read_text()),'review':'The four published images were visually reviewed at full source dimensions; source and neural output retain native 2560x1440. Photographic raw output visibly crushes foliage shadows. No photorealistic gain accepted.'}
    pair = [('playable-source.png',run/'source.bmp','Source game RGB'),('playable-neural.png',run/'output.bmp','Live native Zero-DCE++ bounded output'),('playable-photo-raw.png',ROOT/'runs/adaptive-lut-evaluation-v1/00-companion-hwnd-v1-raw.png','Rejected unrestricted Image-Adaptive-3DLUT CPU output'),('playable-photo-bounded.png',ROOT/'runs/adaptive-lut-evaluation-v1/00-companion-hwnd-v1-bounded.png','Bounded Image-Adaptive-3DLUT CPU output; not integrated')]
    media = ROOT/'docs/media'; manifest = json.loads((media/'manifest.json').read_text())
    for name,source,role in pair:
        target = media/name
        if target.exists(): raise FileExistsError('Already published: '+name)
        if source.suffix=='.png': shutil.copyfile(source,target)
        else: Image.open(source).convert('RGB').save(target)
        manifest['images'].append({'file':name,'sha256':sha(target),'bytes':target.stat().st_size,'dimensions':[2560,1440],'role':role,'source_record':'evidence/playable-live-v1.json','source_artifact':str(source.relative_to(ROOT)).replace('\\','/'),'source_sha256':sha(source),'transformation':'Lossless RGB PNG; no scaling or retouching after the declared model.','license':'Game imagery © Bohemia Interactive; model terms recorded in source evidence'})
    manifest['selection'] += ' Playable loop: first normal-HWND neural snapshot and its exact source, plus both raw and bounded outputs from the first photographic-candidate evaluation. All four reviewed; no quality-based selection.'
    (ROOT/'evidence/playable-live-v1.json').write_text(json.dumps(record,indent=2))
    (media/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({k:record[k] for k in ['gpu_copy_inference_draw_ms']},indent=2))
    print('Published four reviewed stills; latency joined frames:',len(joined))


if __name__=='__main__': main()
