"""Publish bounded RGB-depth feasibility, retained failure and reviewed maps."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr.references import digest,write_json


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def main():
    target=ROOT/'evidence/depth-anything-evaluation-v1.json'
    if target.exists():raise FileExistsError(target)
    plan_path=ROOT/'scenes/playable-depth-evaluation-v1.json';plan=read(plan_path)
    provenance_path=ROOT/'runs/pretrained/depth-anything-v2-small-v1/source.json'
    provenance=read(provenance_path)
    records=[plan_path,provenance_path];evaluations=[];files=[]
    for size in (252,392):
        run=ROOT/f'runs/depth-anything-{size}-v1';measurement=read(run/'report.json')
        geo=ROOT/f'runs/depth-geometry-{size}-v1';geometry=read(geo/'report.json')
        if measurement['status']!='completed' or not measurement['parity_pass']:raise ValueError('Unexpected inference result')
        if measurement['profile_provider_events']!={'DmlExecutionProvider':31}:raise ValueError('Provider events differ')
        if measurement['plan_sha256']!=digest(plan_path) or measurement['provenance_sha256']!=digest(provenance_path):raise ValueError('Changed plan/provenance')
        if measurement['provisional_cost_pass']!=(size==252):raise ValueError('Unexpected cost gate')
        for path,sha in [(run/'model.onnx',measurement['onnx_sha256']),(run/'driver.py',measurement['driver_sha256']),
                (run/measurement['profile_file'],measurement['profile_sha256']),
                (geo/'driver.py',geometry['driver_sha256']),(geo/'samples.json',geometry['samples_sha256']),
                (run/'report.json',geometry['depth_report_sha256'])]:
            if digest(path)!=sha:raise ValueError('Changed retained artifact: '+str(path))
        for i,row in enumerate(measurement['images']):
            for path,sha in [(ROOT/row['source'],row['source_sha256']),
                    (run/f'{i:02d}-input.npy',row['input_sha256']),(run/f'{i:02d}-cpu.npy',row['cpu_sha256']),
                    (run/f'{i:02d}-dml.npy',row['dml_sha256']),(run/f'{i:02d}-full-depth.npy',row['full_depth_sha256']),
                    (run/f'{i:02d}-relative-depth.png',row['visual_sha256'])]:
                if digest(path)!=sha:raise ValueError('Changed image/tensor: '+str(path))
            files.append((run/f'{i:02d}-relative-depth.png',f'depth-{size}-{row["name"]}.png'))
        records.extend([run/'report.json',run/'driver.py',run/measurement['profile_file'],geo/'report.json',geo/'samples.json',geo/'driver.py'])
        evaluations.append({'measurement':measurement,'geometry':geometry})
    failed=ROOT/'runs/depth-anything-392-half-v1';bad=read(failed/'report.json')
    if bad['status']!='failed' or 'fallback to CPU EP' not in bad['error']:raise ValueError('Expected retained provider failure')
    if bad['parent_report_sha256']!=digest(ROOT/'runs/depth-anything-392-v1/report.json'):raise ValueError('Changed parent')
    if digest(failed/'model.onnx')!=bad['onnx_sha256'] or digest(failed/'driver.py')!=bad['driver_sha256']:raise ValueError('Changed failed variant')
    records.extend([failed/'report.json',failed/'driver.py'])
    # The full traceback remains private; its report hash preserves provenance.
    bad_public={k:v for k,v in bad.items() if k!='traceback'}
    finished=datetime.now(timezone.utc)
    elapsed=(finished-datetime.fromisoformat(plan['started_at'].replace('Z','+00:00'))).total_seconds()/60
    report={'schema_version':1,'date':'2026-09-10','outcome':'small_fp32_coarse_depth_feasible_surface_lighting_not_accepted',
        'evaluation_closed_at':finished.isoformat(),'minutes_since_plan_start':elapsed,
        'within_declared_time_bound':elapsed<=plan['maximum_minutes'],'source':provenance,
        'evaluations':evaluations,'half_precision_failure':bad_public,
        'review':{'scope':'Both complete native RGB inputs and all four full-size grayscale depth maps inspected at 1199x658.',
            'closeup':'Both maps retain the main roof plane, wall, foreground pole and broad barrier. Windows and door recesses largely merge into the facade. Roof fittings, antennas and thin barrier details are incomplete; 392 preserves some thin details better.',
            'street':'Road depth gradient and broad building/tree placement are plausible. Foliage becomes smooth masses, with lost gaps. Distant poles, facade openings and railing depth are unresolved or softened.',
            'geometry':'Both pass the predeclared aggregate gate. Of 584 reserved samples, 460 are ground and 124 buildings. Building-only ordering is much weaker than the aggregate; retain the stratified results instead of claiming per-surface geometry correctness.',
            'decision':'Keep the 252 FP32 graph as a candidate coarse RGB-derived depth input. Reject direct normal reconstruction or per-pixel surface relighting from these maps. Close 392 FP32 on cost and the single FP16 graph on no-CPU-fallback failure.',
            'unknown':'Motion stability, HUD effects, additional environments, peak GPU memory, 1440p live input shape/cost, complete application timing and any appearance gain remain unmeasured.'},
        'working_package_changed':False,'new_training_performed':False,
        'source_hashes':{p.relative_to(ROOT).as_posix():digest(p) for p in records},
        'published_media':[{'file':name,'sha256':digest(path),'transformation':'Author bilinear interpolation (align_corners=True) to original 1199x658; independent image min/max to grayscale RGB8-equivalent codes; larger values white. Relative output, no common metric scale.'} for path,name in files]}
    manifest_path=ROOT/'docs/media/manifest.json';manifest=read(manifest_path)
    for path,name in files:
        destination=ROOT/'docs/media'/name
        if destination.exists():raise FileExistsError(name)
        if Image.open(path).size!=(1199,658):raise ValueError('Unexpected image dimensions')
    write_json(target,report)
    for index,(path,name) in enumerate(files):
        destination=ROOT/'docs/media'/name;shutil.copyfile(path,destination)
        manifest['images'].append({'file':name,'sha256':digest(destination),'bytes':destination.stat().st_size,
            'dimensions':[1199,658],'source_record':target.relative_to(ROOT).as_posix(),
            'source_artifact':path.relative_to(ROOT).as_posix(),'source_sha256':digest(path),
            'transformation':report['published_media'][index]['transformation'],
            'rights':'Arma Reforger source imagery © Bohemia Interactive, outside MIT license; Depth Anything V2 Small author model Apache-2.0'})
    write_json(manifest_path,manifest)
    print(json.dumps({'published_images':len(files),'within_time_bound':report['within_declared_time_bound'],'elapsed_minutes':elapsed}))


if __name__=='__main__':main()
