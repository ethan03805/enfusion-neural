"""Close and publish the reviewed offline channel-preservation correction."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import sys

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr.references import digest,write_json
from scripts.publish_sustained import publication_copy


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    target=ROOT/'evidence/playable-dce-channel-guard-v1.json'
    if target.exists():
        raise FileExistsError(target)
    run=ROOT/'runs/dce-channel-guard-v1'; review_root=ROOT/'runs/dce-channel-guard-review-v1'
    plan_path=ROOT/'scenes/playable-dce-channel-guard-v1.json'
    plan=read(plan_path); result=read(run/'report.json'); review=read(review_root/'report.json')
    if result['status']!='completed' or not result['all_gates_pass'] or len(result['frames'])!=600 or len(result['control_frames'])!=600:
        raise ValueError('Guard did not pass the complete declared evaluation')
    checks=[(plan_path,result['plan_sha256']),(run/'driver.py',result['driver_sha256']),
            (run/'report.json',review['measurement_sha256']),
            (ROOT/'scripts/review_dce_channel_guard.py',review['driver_sha256'])]
    checks += [(run/name,sha) for name,sha in result['retained_hashes'].items()]
    checks += [(ROOT/name,sha) for name,sha in result['candidate_hashes'].items()]
    checks += [(ROOT/r['path'],r['sha256']) for key in ['fixture_images','keys','aids'] for r in review[key]]
    checks += [(run/name,sha) for name,sha in plan['retained_originals'].items()]
    for path,sha in checks:
        if digest(path)!=sha:
            raise ValueError('Changed evidence: '+path.name)
    for name,sha in plan['source_hashes'].items():
        path=run/'original-companion.cpp' if name=='native/companion.cpp' else ROOT/name
        if digest(path)!=sha:
            raise ValueError('Changed original source dependency: '+name)
    groups={}
    for r in review['fixture_images']:
        groups.setdefault(r['sha256'],[]).append(r['path'])
    if len(groups)!=4:
        raise ValueError('Unexpected unique fixture images; repeat visual review before publication')
    closed=datetime.now(timezone.utc)
    minutes=(closed-datetime.fromisoformat(plan['started_at'])).total_seconds()/60
    decision={
        'recorded_at':closed.isoformat(),'accepted_scope':'Accept the single offline headroom correction for separate live validation. The published playable ZIP is not replaced.',
        'review_scope':'All four complete native 2560x1440 source/original/guarded gameplay triplets inspected, plus all ten chronological one-second contact triplets and the poster. All six fixture pairs covered by their four unique full-size PNGs: source/identity/invalid outputs share exact file hashes, and both dark outputs share an exact file hash. Each distinct complete fixture image inspected.',
        'visual_result':'The guarded gameplay keys remain visually close to the original DCE result; buildings, doors/windows, roof patterns, foliage, barriers, lettering and HUD retain their visible arrangement. The recorded difference affects 162,334,246,277 pixels in the four keys. Source blur and aliasing persist. The synthetic bright fixture shows less saturation while preserving the palette layout; dark output is byte-identical to its original. No broad new seam is apparent in these samples.',
        'limits':'This is a numerical source-color correction, not substantial photorealistic material/lighting gain, full temporal acceptance or semantic visibility proof. No complete real-time perceptual playback review is claimed. Zero endpoint clipping is established for this 600-frame sequence and fixed fixtures, not all possible gameplay. Original CPU full-composition bias remains unresolved.',
        'performance_scope':'Offline replay includes upload/readback, curve dumps and CPU checks. Do not infer live application performance or latency from its timings. Native source build changed; existing downloadable ZIP and prior live benchmark records remain unchanged.',
        'next':'Run a separately bounded live validation of capture/output parity, source bypass, enhancement modes, exit, foreground handling and complete application cadence before rebuilding the download.',
        'photorealistic_gain_accepted':False,'full_temporal_acceptance':False,'live_validation_complete':False,
    }
    write_json(review_root/'decision.json',decision)
    files=[(review_root/'poster.png','dce-channel-guard-poster.png','Area-reduced source/original/guarded comparison at seven seconds, 896x504 per panel plus labels.'),
           (run/'key-0420-guarded.png','dce-channel-guard-reserved.png','Unchanged native 2560x1440 D3D11 guarded replay output at seven seconds; source and original are retained in the paired-temporal publication.'),
           (run/'fixture-source.png','dce-channel-guard-fixture-source.png','Unchanged original 2560x1440 synthetic source palette, 1728 declared RGB colors in repeated tiles.'),
           (run/'fixture-bright-original.png','dce-channel-guard-fixture-original.png','Unchanged native 2560x1440 original compositor output for the deliberately bright constant-curve fixture, including its clipping failure.'),
           (run/'fixture-bright-guarded.png','dce-channel-guard-fixture-corrected.png','Unchanged native 2560x1440 guarded compositor output for the same constant-curve fixture.')]
    report={'schema_version':1,'date':'2026-09-10','outcome':'offline_channel_guard_pass_live_validation_pending',
            'closed_at':closed.isoformat(),'minutes_since_original_start':minutes,'within_declared_bound':minutes<=30,
            'plan':plan,'measurement':result,'visual_review':review,'decision':decision,
            'fixture_image_equivalence':groups,'download_changed':False,'native_source_changed':True,
            'validation':'Native Release companion/replay build succeeds. All 79 Python tests and 12 malformed native-record checks pass. The RX7800XT paired replay and fixtures provide the GPU evidence; CPU tests alone do not.',
            'source_hashes':{p.relative_to(ROOT).as_posix():digest(p) for p in [plan_path,run/'report.json',review_root/'report.json',review_root/'decision.json',Path(__file__),ROOT/'tests/test_exposure_guard.py']},
            'published_media':[]}
    manifest_path=ROOT/'docs/media/manifest.json'; manifest=read(manifest_path)
    entries=[]
    for path,name,transform in files:
        if (ROOT/'docs/media'/name).exists():
            raise FileExistsError(name)
        entry={'file':name,'sha256':digest(path),'bytes':path.stat().st_size,'dimensions':list(Image.open(path).size),
               'source_record':target.relative_to(ROOT).as_posix(),'source_artifact':path.relative_to(ROOT).as_posix(),'source_sha256':digest(path),'transformation':transform,
               'rights':'Original procedural fixture, MIT code license.' if 'fixture' in name else 'Arma Reforger imagery © Bohemia Interactive, outside MIT code license. Zero-DCE++ checkpoint has separate academic/noncommercial terms.'}
        entries.append((path,entry)); report['published_media'].append(entry)
    safe=publication_copy(report,[(ROOT.as_posix(),'.'),(Path.home().as_posix(),'<USER_HOME>')])
    for path,entry in entries:
        shutil.copyfile(path,ROOT/'docs/media'/entry['file']); manifest['images'].append(entry)
    write_json(target,safe); write_json(manifest_path,manifest)
    print(json.dumps({'minutes_since_original_start':minutes,'within_bound':minutes<=30,'published_images':len(entries),'all_gates_pass':result['all_gates_pass']}))


if __name__=='__main__':
    main()
