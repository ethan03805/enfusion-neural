"""Publish the paired replay diagnostic, CPU failure and clipping limitation."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr.references import digest,write_json
from scripts.publish_sustained import publication_copy


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    target=ROOT/'evidence/playable-dce-temporal-v2.json'
    if target.exists():
        raise FileExistsError(target)
    run=ROOT/'runs/dce-temporal-native-v2'; review=ROOT/'runs/dce-temporal-review-v2'
    plan_path=ROOT/'scenes/playable-dce-temporal-native-v2.json'
    plan=read(plan_path); result=read(run/'report.json'); visual=read(review/'report.json')
    original=read(ROOT/'runs/dce-temporal-v1/report.json')
    if result['status']!='completed' or visual['status']!='completed' or len(result['frames'])!=600:
        raise ValueError('Incomplete diagnostic')
    if original['status']!='failed' or original['frames'] or original['parity']['passes']:
        raise ValueError('Original CPU failure not retained')
    checks=[(plan_path,result['plan_sha256']),(run/'driver.py',result['driver_sha256']),
            (run/'report.json',visual['parent_report_sha256']),(review/'comparison.mp4',visual['video_sha256']),
            (ROOT/'scenes/playable-dce-temporal-v1.json',plan['amendment']['parent_plan_sha256']),
            (ROOT/'runs/dce-temporal-v1/report.json',plan['amendment']['failed_cpu_report_sha256'])]
    checks += [(ROOT/name,sha) for name,sha in plan['source_hashes'].items()]
    checks += [(run/name,sha) for name,sha in result['retained_hashes'].items()]
    checks += [(review/row['file'],row['sha256']) for row in visual['review_images']]
    checks += [(run/row['file'],row['sha256']) for row in visual['keys']]
    for path,sha in checks:
        if digest(path)!=sha:
            raise ValueError('Changed evidence: '+path.name)
    if not result['parity']['passes'] or not result['sensitivity_controls_pass'] or not visual['timestamp_check']['passes']:
        raise ValueError('Required reproduction/control/timestamp check failed')
    fields=np.load(run/'curves.npy',mmap_mode='r')
    for i in range(600):
        native=np.fromfile(run/'native-curves'/f'curve-{i+1:06d}.f32',dtype='<f4').reshape(3,180,320)
        if not np.array_equal(native,fields[i]):
            raise ValueError('Native curve sequence differs')
    clipping=read(run/'clipping-diagnostic.json')
    clipping['fixed_key_examples']=[]
    for i in [0,180,420,599]:
        x=np.array(Image.open(run/f'key-{i:04d}-source.png').convert('RGB'))
        y=np.array(Image.open(run/f'key-{i:04d}-enhanced.png').convert('RGB'))
        changed=((y==0)|(y==255))&((x>0)&(x<255))
        positions=np.argwhere(changed)
        examples=[]
        for row,col,channel in positions[:5]:
            examples.append({'x':int(col),'y':int(row),'channel':int(channel),'source_rgb8':x[row,col].tolist(),'output_rgb8':y[row,col].tolist()})
        clipping['fixed_key_examples'].append({'frame':i,'newly_clipped_channels':int(changed.sum()),'first_five_channel_locations':examples})
    closed=datetime.now(timezone.utc)
    minutes=(closed-datetime.fromisoformat(plan['started_at'])).total_seconds()/60
    decision={
        'recorded_at':closed.isoformat(), 'decision':'Accept the bounded coarse added-exposure diagnostic only; full fidelity and photorealistic acceptance remain open.',
        'review_scope':'Ten chronological one-second comparison samples at 448x252 per panel, all four complete native 2560x1440 source/enhanced key pairs at 0,3,7,9.983 seconds, and the 1792x536 poster inspected. No complete real-time perceptual playback review or all-frame visual inspection is claimed.',
        'observations':'Source and enhanced keys keep the same visible openings, roof patterns, poles, barrier bars and foliage arrangement. Enhancement slightly lifts road/wall/vegetation midtones. Source peripheral blur and fine aliasing remain. No obvious broad exposure discontinuity appears in the contact samples; samples cannot establish absence of flicker. Fixed HUD margins taper the effect. No photorealistic material/lighting gain is accepted.',
        'clipping_limit':'Numerical review finds newly endpoint-clipped individual channels on every frame. The four fixed keys show new white endpoints and no new black endpoints; the full-sequence aggregate combines both endpoints. This is a separate color-preservation defect despite low coarse exposure variation.',
        'correspondence_limit':'448x252 source-only optical flow with photometric/gradient/closure exclusions and a limited screen region. Coverage is a fraction of that region, not the entire image. Thin cover, disocclusions, hidden targets and HUD transitions are not accepted.',
        'cpu_failure':'Original CPU composition differs by at most one RGB8 code, mean .033434 versus the frozen .02 ceiling. Curves pass; the cause of the mostly positive composition bias is not isolated. Retain the failed result. Native replay matches the same saved native RGB and curves exactly; thresholds and original deadline remain unchanged.',
        'runtime_limit':'One native parity frame plus 600 replay frames, game stopped. Offline upload, file dumps and CPU readback are not live performance or latency. Working package and live shader remain unchanged.',
        'full_temporal_acceptance':False,'photorealistic_gain_accepted':False,
    }
    write_json(review/'decision.json',decision)
    files=[(review/'comparison.mp4','dce-temporal-unretimed.mp4','video'),
           (review/'poster.png','dce-temporal-poster.png','poster'),
           (run/'key-0420-source.png','dce-temporal-reserved-source.png','source'),
           (run/'key-0420-enhanced.png','dce-temporal-reserved-enhanced.png','enhanced')]
    report={'schema_version':1,'date':'2026-09-10','outcome':'coarse_exposure_variation_pass_with_clipping_defect',
        'evaluation_closed_at':closed.isoformat(),'minutes_since_original_plan_start':minutes,'within_declared_time_bound':minutes<=plan['maximum_minutes'],
        'plan':plan,'original_cpu_failure':original,'original_cpu_diagnostic':read(ROOT/'runs/dce-temporal-v1/parity-diagnostic.json'),
        'native_measurement':result,'video':visual,'review':decision,'clipping':clipping,
        'working_package_changed':False,'live_shader_changed':False,'published_media':[],
        'source_hashes':{p.relative_to(ROOT).as_posix():digest(p) for p in [plan_path,run/'report.json',review/'report.json',review/'decision.json',run/'clipping-diagnostic.json',Path(__file__)]}}
    manifest_path=ROOT/'docs/media/manifest.json'; manifest=read(manifest_path)
    entries=[]
    for path,name,kind in files:
        if (ROOT/'docs/media'/name).exists():
            raise FileExistsError(name)
        transform=visual['transformation'] if kind=='video' else ('Unchanged area-reduced 1792x536 source/native-replay comparison PNG at three seconds, including labels.' if kind=='poster' else 'Unchanged native 2560x1440 '+('source RGB decoded from retained gameplay video.' if kind=='source' else 'D3D11 replay output at seven seconds; existing network and shader, not a new gameplay capture.'))
        entry={'file':name,'sha256':digest(path),'bytes':path.stat().st_size,
               'dimensions':[1792,536] if kind=='video' else list(Image.open(path).size),
               'source_record':target.relative_to(ROOT).as_posix(),'source_artifact':path.relative_to(ROOT).as_posix(),
               'source_sha256':digest(path),'transformation':transform,
               'rights':'Arma Reforger imagery © Bohemia Interactive, outside MIT code license. Zero-DCE++ author checkpoint has separate academic/noncommercial terms.'}
        if kind=='video':
            entry.update(duration_seconds=10,playback_speed=1,retimed=False)
        entries.append((path,entry,kind)); report['published_media'].append(entry)
    safe=publication_copy(report,[(ROOT.as_posix(),'.'),(Path.home().as_posix(),'<USER_HOME>')])
    for path,entry,kind in entries:
        shutil.copyfile(path,ROOT/'docs/media'/entry['file'])
        manifest['videos' if kind=='video' else 'images'].append(entry)
    write_json(target,safe); write_json(manifest_path,manifest)
    print(json.dumps({'minutes_since_original_start':minutes,'within_bound':minutes<=30,'newly_clipped_samples':clipping['total_newly_clipped_channel_samples'],'published_files':len(entries)}))


if __name__=='__main__':
    main()
