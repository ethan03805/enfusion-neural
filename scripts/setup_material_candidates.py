"""Create the bounded native material candidate experiment with fixed environment."""
import argparse
import json
from pathlib import Path
import shutil
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import lab_modules, digest, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True); p.add_argument('--lab-source', required=True)
    a = p.parse_args(); out = a.out.resolve()
    if out.exists() and any(out.iterdir()): raise FileExistsError(out)
    plan_path = ROOT / 'scenes/playable-material-candidates-v1.json'; plan = json.loads(plan_path.read_text())
    initialize, _, doctor = lab_modules(a.lab_source); detected = doctor()
    if not detected['workbench_available']: raise ValueError('Workbench unavailable')
    initialize(out)
    source = ROOT / 'adapters/enfusion/probes/ENR_MaterialCandidates.c'
    game = out / 'addon/Scripts/Game'; shutil.copyfile(source, game / source.name)
    capture = game / 'ELab_GameCapture.c'
    script = (ROOT / 'adapters/enfusion/ELab_GameCapture.c').read_text()
    marker = '  if (ELab_CaptureState.Elapsed < ELab_CaptureState.Delay)\n   return;\n  ELab_CaptureState.Armed = false;'
    if script.count(marker) != 1: raise ValueError('Unexpected reference capture adapter')
    capture.write_bytes(script.replace(marker, marker.replace('  ELab_CaptureState.Armed = false;', '  if (!ENR_MaterialCandidates.Step(world, timeslice)) return;\n  ELab_CaptureState.Armed = false;')).encode())
    config = game / 'ENR_ReferenceConfig.c'
    config.write_text('#ifdef WORKBENCH\nclass ENR_ReferenceConfig { static int Year=1989; static int Month=6; static int Day=21; static float Hour=13; static float WindSpeed=0; static float WindDirection=0; static string Weather="Clear"; }\n#endif\n')
    refs = ROOT / 'runs/slate-photo-references-v1'
    reference_files = [('cupa12-detail.png','https://www.cupapizarras.com/wp-content/uploads/2024/02/cupa-12-slate-detail.png'), ('cupa12-roof.jpg','https://www.cupapizarras.com/wp-content/uploads/2025/09/grand-designs-partner-slate-roof.jpg')]
    ref_record = {'source_page': plan['reference']['product_page'], 'retrieved_date':'2026-09-10', 'files':[],
        'review':'Both original images inspected. Small slate sample is dark grey with modest broad reflection and fine surface variation; installed roof is blue-grey with low sheen and distinct tiles. Lighting/exposure/wear are unmatched. No inferred numerical roughness.',
        'publication':'Private inspection only; author links in documentation, no image redistribution or training.'}
    for name, url in reference_files:
        path = refs / name
        with Image.open(path) as image:
            ref_record['files'].append({'file':name,'url':url,'sha256':digest(path),'bytes':path.stat().st_size,'dimensions':list(image.size)})
    if not (refs / 'reference.json').exists(): write_json(refs / 'reference.json', ref_record)
    shutil.copyfile(__file__, out / 'setup-driver.py')
    write_json(out / 'setup.json', {'doctor':detected, 'plan':plan, 'reference':ref_record,
        'source_hashes': {path.relative_to(ROOT).as_posix():digest(path) for path in [source, capture, config, plan_path, Path(__file__), refs / 'reference.json']}})
    print(str(out))


if __name__ == '__main__': main()
