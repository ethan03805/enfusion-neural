"""Retain the rejected moderate roof candidates and selection-before-reserved record."""
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json


def read(path): return json.loads(path.read_text(encoding='utf-8'))


def main():
    target = ROOT / 'evidence/playable-material-candidates-v1.json'
    if target.exists(): raise FileExistsError(target)
    project = ROOT / 'runs/playable-material-candidates-v1'; setup = read(project/'setup.json')
    selection_path = project/'selection-before-reserved.json'; selection = read(selection_path)
    reports = [read(ROOT/f'runs/material-candidates-{view}-v1/report.json') for view in ['closeup','approach','reverse']]
    for record in [setup,selection]+reports:
        for path, sha in record['source_hashes'].items():
            if digest(ROOT/path) != sha: raise ValueError('Recorded source changed: '+path)
    validation = read(project/'runs/20260910T090544-f11a4aa5f1/run.json')
    runs = [read(project/'runs'/r['run']/'run.json') for r in reports]
    if validation['status'] != 'succeeded' or validation['process_exit_code'] != 0: raise ValueError('Validation failed')
    if any(r['addon_sha256'] != validation['addon_sha256'] for r in runs): raise ValueError('Capture differs from validation')
    if not datetime.fromisoformat(selection['date']) < datetime.fromisoformat(runs[2]['started_at']): raise ValueError('Selection was not reserved')
    if selection['selected_for_reserved_check'] != .7 or not reports[0]['numeric_gates_pass']: raise ValueError('Selection/controls differ')
    sources = [project/'setup.json',selection_path,project/'runs/20260910T090544-f11a4aa5f1/run.json',
        project/'runs/20260910T090544-f11a4aa5f1/console.log']
    sources += [ROOT/f'runs/material-candidates-{view}-v1/report.json' for view in ['closeup','approach','reverse']]
    files = []
    for index, names in [(0,['source','candidate040','candidate070']), (2,['source','candidate070','restored'])]:
        for name in names:
            row = reports[index]['images'][name]; path=ROOT/row['path']
            files.append((path,f'roof-candidates-{reports[index]["view"]}-{name}.png'))
    reference = setup['reference']
    for row in reference['files']:
        if digest(ROOT/'runs/slate-photo-references-v1'/row['file']) != row['sha256']: raise ValueError('Reference bytes changed')
    report = {'schema_version':1,'date':'2026-09-10','outcome':'moderate_roughness_candidates_rejected_keep_original',
        'plan':setup['plan'],'reference':reference,'selection_before_reserved':selection,'views':reports,
        'validation':{k:validation.get(k) for k in ['run_id','status','process_exit_code','wall_seconds','addon_sha256']},
        'captures':[{k:r.get(k) for k in ['run_id','status','wall_seconds','started_at','finished_at','terminated_owned_process','process_exit_code']} for r in runs],
        'review':{'inspected':'All 12 original source/candidate040/candidate070/reset captures reviewed in full at native 1199x658; both manufacturer reference images inspected privately.',
            'selection_views':'0.4 is too pale and reflective, particularly on the extension roof. 0.7 gives a smaller cooler sheen and was provisionally selected before the reserved sequence.',
            'reserved_view':'0.7 adds a broad pale response across the close roof slope and reduces the visible weathered slate contrast. Tile outlines, roof attachments and foreground cover remain present, but a convincing appearance benefit is absent. Reject the fixed candidate; do not select another value after seeing this view.',
            'numerical':'Camera, date, hour, weather, wind and reported HDR brightness remain fixed within each sequence. No new clipped channels in any full-frame candidate comparison. Close-up reset roof MAE 0.0598 codes. Full-frame temporal differences remain; maxima are not hidden by alignment.',
            'decision':'Keep original roof roughness. The working material API is retained, but no optional preset, training target or live change is justified by these candidates.',
            'scope':'This closes the declared scalar candidates, not every possible native material workflow. Photographs are unmatched appearance guidance; neither a numerical roughness calibration nor photorealistic ground truth.'},
        'source_hashes':{p.relative_to(ROOT).as_posix():digest(p) for p in sources},
        'published_media':[{'file':name,'sha256':digest(path),'transformation':'Unchanged native Workbench PNG; no scaling, alignment, grading or neural processing'} for path,name in files],
        'working_package_changed':False,'new_training':False,'photorealistic_gain_accepted':False,
        'next':'Bounded RGB monocular-depth evaluation against existing offline collision samples before any neural lighting composition. Keep geometry mismatch and unknown scale explicit.'}
    write_json(target,report)
    manifest_path=ROOT/'docs/media/manifest.json'; manifest=read(manifest_path)
    for path,name in files:
        destination=ROOT/'docs/media'/name
        if destination.exists(): raise FileExistsError(name)
        shutil.copyfile(path,destination)
        manifest['images'].append({'file':name,'sha256':digest(destination),'bytes':destination.stat().st_size,
            'dimensions':list(Image.open(destination).size),'source_record':target.relative_to(ROOT).as_posix(),
            'source_artifact':path.relative_to(ROOT).as_posix(),'source_sha256':digest(path),
            'transformation':'Unchanged native Workbench screenshot; no resizing or neural processing',
            'rights':'Arma Reforger imagery © Bohemia Interactive, outside MIT license'})
    write_json(manifest_path,manifest)
    print('Published all three candidate evaluations, frozen selection, rejection and six reviewed native images.')


if __name__ == '__main__': main()
