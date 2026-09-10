"""Publish the reviewed live correction and a byte-verified runnable package."""
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import shutil
import sys
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr.references import digest,write_json
from scripts.publish_sustained import publication_copy

def read(path): return json.loads(path.read_text(encoding='utf-8'))

def main():
    target=ROOT/'evidence/playable-live-guard-v1.json'
    package_target=ROOT/'evidence/playable-package-v2.json'
    if target.exists() or package_target.exists(): raise FileExistsError('Publication already exists')
    run=ROOT/'runs/live-guard-v1'; review_root=ROOT/'runs/live-guard-review-v2'
    plan_path=ROOT/'scenes/playable-live-guard-v1.json'
    plan=read(plan_path); evaluation=read(run/'evaluation.json'); review=read(review_root/'report.json')
    package=read(ROOT/'runs/guarded-package-audit-v1/report.json')
    if not evaluation['all_gates_pass'] or package['status']!='passed' or not review['timestamp_check']['passes']:
        raise ValueError('Release gates failed')
    if evaluation['plan_sha256']!=digest(plan_path) or review['evaluation_sha256']!=digest(run/'evaluation.json'):
        raise ValueError('Changed evaluation')
    for name,sha in plan['processing_hashes'].items():
        if digest(ROOT/name)!=sha: raise ValueError('Changed frozen dependency: '+name)
    for name,sha in evaluation['source_hashes'].items():
        path=run/'evaluation-driver-original.py' if name=='scripts/evaluate_live_guard.py' else ROOT/name
        if digest(path)!=sha: raise ValueError('Changed original evidence: '+name)
    for row in review['keys']+review['aids']:
        if digest(review_root/row['file'])!=row['sha256']: raise ValueError('Changed reviewed image')
    if digest(review_root/'gameplay.mp4')!=review['video_sha256']: raise ValueError('Changed video')
    events=(run/'companion/events.log').read_text()
    if 'presentation wait timeout ' in events:
        raise ValueError('Raw event audit found a timeout')
    hide_times=[float(x) for x in re.findall(r'^hide ([0-9.]+)$',events,re.M)]
    bypass_time=float(re.search(r'^bypass 1 ([0-9.]+)$',events,re.M)[1])
    start,end=evaluation['analysis']['window']['qpc_ms']
    if len(hide_times)!=1 or not hide_times[0]>end or hide_times[0]<bypass_time:
        raise ValueError('Unexpected hide event')
    closed=datetime.now(timezone.utc)
    minutes=(closed-datetime.fromisoformat(plan['started_at'])).total_seconds()/60
    if minutes>30: raise TimeoutError('Do not publish as a within-bound release')
    failure={'status':'failed_retained','run':'runs/live-guard-review-v1',
             'reason':'The rawvideo decoder omitted fps_mode passthrough, so FFmpeg duplicated VFR frames. The unexpected trailing bytes fail the frame-count guard. Its sampled keys are not accepted or published.',
             'recovery':'Explicit timestamp passthrough in review-v2, same original recording and original deadline. All 1855 video PTS match exactly. No game rerun or shader/model change.',
             'retained_files':{p.name:digest(p) for p in (ROOT/'runs/live-guard-review-v1').iterdir() if p.is_file()}}
    write_json(ROOT/'runs/live-guard-review-v1/failure.json',failure)
    decision={'closed_at':closed.isoformat(),'minutes_since_original_start':minutes,'within_bound':True,
              'accepted_scope':'Release the guarded exposure companion after the fixed live correctness, controls and cadence checks; substantial photorealistic appearance remains unfinished.',
              'visual_review':'Inspected all 34 chronological one-second contact samples, four complete native 2560x1440 decoded video keys, the poster and complete native source/guarded snapshot pair. Snapshot pair also viewed as tool-reduced full images. No complete 1x perceptual playback claim.',
              'observations':'Street movement and the camera turn are visible. Buildings, roof patterns, doors/windows, rails, poles, foliage and painted signs retain their visible arrangement. Exposure is modest; peripheral movement blur, roof/foliage aliasing and video compression remain visible. The snapshot brightens surfaces without new channel endpoints. No substantial material/lighting gain or semantic target-visibility acceptance.',
              'control_method':'Sky sent F8, F8, F9, F9, F10 to the observed game window after measurement. Fresh screenshots followed each action. Native logs/frames confirm bypass/resume and modes 3,0,3. Companion exits 0; the owned game remains alive five seconds later, then the driver closes its own game.',
              'f8_handler_to_hide_ms':hide_times[0]-bypass_time,
              'latency_limit':'Hotkey handler-to-hide is software logging, not physical key or panel latency. Moving capture-to-display and physical WASD/mouse remain unverified.',
              'download':'New ZIP includes the exact tested executable, complete CMake target sources, launcher, isolated addon, model attribution and hashes. Old ZIP remains unchanged.',
              'analysis_audit':'Correct the evaluator timeout spelling to native presentation wait timeout. The original driver/report are retained. Independent raw-log audit confirms no timeout anywhere and only the intended post-measurement bypass hide; acceptance results do not change.'}
    write_json(review_root/'decision.json',decision)
    report={'schema_version':1,'date':'2026-09-10','outcome':'live_guard_pass_guarded_package_released','plan':plan,'evaluation':evaluation,
            'review':review,'decision':decision,'retained_review_failure':failure,'download_record':'evidence/playable-package-v2.json',
            'negative_age_count':len(evaluation['negative_capture_age_frames']),
            'recording_cost':'Native 1440p AMF recording includes GPU capture, CPU download/color conversion and GPU encode. All reported live rates include this cost. There is no matched unrecorded pass for the guard; no subtraction-based recording cost is claimed.',
            'source_hashes':{p.relative_to(ROOT).as_posix():digest(p) for p in [plan_path,run/'evaluation.json',review_root/'report.json',review_root/'decision.json',Path(__file__),ROOT/'scripts/evaluate_live_guard.py',ROOT/'runs/guarded-package-audit-v1/report.json']},
            'published_media':[]}
    images=[(review_root/'poster.png','live-guard-poster.png','Area-reduced 1280x720 native video key at 10 seconds.'),
            (run/'source.png','live-guard-source.png','Unchanged RGB PNG conversion of native 2560x1440 source BMP, post-measurement.'),
            (run/'guarded.png','live-guard-output.png','Unchanged RGB PNG conversion of native 2560x1440 guarded output BMP for the same frame.')]
    manifest=read(ROOT/'docs/media/manifest.json')
    entries=[]
    rights='Arma Reforger imagery © Bohemia Interactive, outside MIT code license. Zero-DCE++ weights have separate academic/noncommercial research terms.'
    for source,name,transform in images+[(review_root/'gameplay.mp4','live-guard-unretimed.mp4',review['transformation'])]:
        entry={'file':name,'sha256':digest(source),'bytes':source.stat().st_size,
               'dimensions':[1280,720] if name.endswith('.mp4') else list(Image.open(source).size),
               'source_record':target.relative_to(ROOT).as_posix(),'source_artifact':source.relative_to(ROOT).as_posix(),
               'source_sha256':digest(source),'transformation':transform,'rights':rights}
        if name.endswith('.mp4'): entry.update(duration_seconds=34,playback_speed=1,retimed=False)
        if (ROOT/'docs/media'/name).exists(): raise FileExistsError(name)
        entries.append((source,entry)); report['published_media'].append(entry)
    safe=publication_copy(report,[(ROOT.as_posix(),'.'),(Path.home().as_posix(),'<USER_HOME>')])
    archive=ROOT/'runs/deliverables/Enfusion-Neural-Playable-2026-09-10-Guarded.zip'
    if digest(archive)!=package['sha256']: raise ValueError('Changed archive')
    for source,entry in entries:
        shutil.copyfile(source,ROOT/'docs/media'/entry['file'])
        manifest['videos' if entry['file'].endswith('.mp4') else 'images'].append(entry)
    shutil.copyfile(archive,ROOT/'docs/downloads'/package['download_file'])
    write_json(target,safe); write_json(package_target,package); write_json(ROOT/'docs/media/manifest.json',manifest)
    print(json.dumps({'minutes':minutes,'package_sha256':package['sha256'],'negative_capture_age_frames':report['negative_age_count'],'F8_handler_to_hide_ms':decision['f8_handler_to_hide_ms']}))

if __name__=='__main__': main()
