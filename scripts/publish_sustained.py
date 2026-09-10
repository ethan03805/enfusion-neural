"""Publish the completed sustained gameplay comparison and explicit review limits."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def publication_copy(value, replacements):
    """Keep machine paths in retained local records, with their original hashes."""
    if isinstance(value, dict):
        return {publication_copy(k, replacements): publication_copy(v, replacements) for k, v in value.items()}
    if isinstance(value, list):
        return [publication_copy(v, replacements) for v in value]
    if isinstance(value, str):
        value = value.replace('\\', '/')
        for source, label in replacements:
            value = value.replace(source, label)
        value = re.sub(r'app1874880_user\d+', 'app1874880_user<ACCOUNT>', value)
        if re.search(r'[A-Za-z]:/', value):
            raise ValueError('Unredacted machine path in publication: ' + value[:180])
    return value


def main():
    target = ROOT/'evidence/playable-sustained-v2.json'
    if target.exists(): raise FileExistsError(target)
    plan_path = ROOT/'scenes/playable-sustained-v2.json'; plan = read(plan_path)
    analysis_path = ROOT/'runs/sustained-comparison-v2.json'; analysis = read(analysis_path)
    review_root = ROOT/'runs/sustained-review-v3'; review = read(review_root/'report.json'); decision = read(review_root/'decision.json')
    composed_root = ROOT/'runs/sustained-comparison-web-v2'; composed = read(composed_root/'manifest.json')
    if digest(plan_path) != analysis['plan_sha256'] or len(analysis['runs']) != 3:
        raise ValueError('Missing fixed comparison')
    if digest(review_root/'report.json') != decision['review_report_sha256']:
        raise ValueError('Review evidence changed')
    expected = [('standard','off'),('combined','off'),('combined','neural')]
    records = [plan_path, analysis_path, review_root/'report.json', review_root/'decision.json', composed_root/'manifest.json', Path(__file__)]
    for row, config, reviewed in zip(analysis['runs'], expected, review['runs']):
        root = ROOT/'runs'/row['run']; m = row['measurement']; launch = read(root/'launch.json')
        if (m['preset'],m['mode']) != config or not m['recording'] or m['window']['simulation_s'] != [30,210] or reviewed['run'] != row['run']:
            raise ValueError('Wrong pass identity/window')
        for name, sha in m['source_hashes'].items():
            if digest(root/name) != sha: raise ValueError('Changed measurement artifact: '+name)
        if digest(root/'gameplay.mp4') != reviewed['source_sha256'] or digest(root/'gameplay.mp4') != composed['sources'][(root/'gameplay.mp4').relative_to(ROOT).as_posix()]:
            raise ValueError('Changed recorded source')
        for key in ('sheets','keys'):
            for entry in reviewed[key]:
                if digest(review_root/entry['file']) != entry['sha256']: raise ValueError('Changed reviewed image')
        row.update(processing_hashes=launch['processing_hashes'], addon_hashes=launch['addon_hashes'],
                   benchmark_driver_sha256=digest(root/'benchmark-driver.py'))
        if not row['game_foreground_through_measurement']:
            raise ValueError('Foreground evidence does not establish a controlled final pass')
        records.extend([root/'launch.json',root/'benchmark-driver.py'])
        if config[1] == 'neural':
            companion = read(root/'companion/run.json'); events = (root/'companion/events.log').read_text()
            if companion['adapter'] != 'AMD Radeon RX 7800 XT' or [companion['width'],companion['height']] != [2560,1440] or companion['initial_mode'] != 3:
                raise ValueError('Unexpected companion configuration')
            complete = re.search(r'complete frames (\d+) elapsed_ms ([\d.]+)',events)
            row['companion_session'] = {'configuration':companion,'events':events,
                'complete':bool(complete),'whole_session_frames':int(complete[1]) if complete else None,
                'whole_session_elapsed_ms':float(complete[2]) if complete else None,
                'hide_events':len(re.findall(r'^hide ',events,re.M)),
                'presentation_wait_timeouts':events.count('presentation wait timeout'),
                'bypass_events':len(re.findall(r'^bypass ',events,re.M))}
            records.extend([root/'companion/run.json',root/'companion/events.log'])
    video = composed_root/'comparison.mp4'
    if digest(video) != composed['output_sha256'] or video.stat().st_size >= 100*1024*1024 or abs(float(composed['probe']['duration'])-184) > .04 or composed['nonpositive_intervals']:
        raise ValueError('Invalid video integrity/duration')
    validation = ROOT/'runs/sustained-validation-v2/runs/20260910T111535-23c8dfec02'
    valid = read(validation/'run.json')
    if valid['status'] != 'succeeded' or valid['process_exit_code'] != 0 or valid['terminated_owned_process']:
        raise ValueError('Failed addon validation')
    records.extend([validation/'run.json',validation/'console.log'])
    pilot_root = ROOT/'runs/sustained-pilot-review-v1'
    records.extend([ROOT/'runs/sustained-pilot-analysis-v1.json',pilot_root/'report.json',pilot_root/'decision.json',ROOT/'runs/sustained-pilot-v1/benchmark-driver.py'])
    closed = datetime.now(timezone.utc)
    elapsed = (closed-datetime.fromisoformat(plan['started_at'].replace('Z','+00:00'))).total_seconds()/60
    initial = ROOT/'runs/sustained-neural-v1'
    initial_failure = read(initial/'launch.json')
    if initial_failure['status'] != 'failed': raise ValueError('Expected retained initial enhancement failure')
    recovery = read(ROOT/'runs/sustained-recovery-v1.json')
    records.extend([ROOT/'scenes/playable-sustained-v1.json', ROOT/'runs/sustained-two-pass-v1.json',
                    initial/'launch.json',initial/'recording.log',initial/'companion/events.log',
                    initial/'companion/run.json',ROOT/'runs/sustained-standard-analysis-v2.json',
                    ROOT/'runs/sustained-recovery-v1.json'])
    records.append(ROOT/'runs/sustained-telemetry-diagnostic-v1.json')
    report = {'schema_version':1,'date':'2026-09-10','evaluation_closed_at':closed.isoformat(),
        'minutes_since_plan_start':elapsed,'within_declared_time_bound':elapsed<=plan['maximum_minutes'],
        'plan':plan,'comparison':analysis,'review_artifacts':review,'review_decision':decision,'video':composed,
        'pilot':{'measurement':read(ROOT/'runs/sustained-pilot-analysis-v1.json'),'review':read(pilot_root/'decision.json')},
        'addon_validation':valid,'route_amendments':0,'measurement_amendments':1,
        'initial_two_pass_comparison':read(ROOT/'runs/sustained-two-pass-v1.json'),
        'initial_enhancement_failure':{'launch':initial_failure,'events':(initial/'companion/events.log').read_text(),
            'recording_error':(initial/'recording.log').read_text(),'scope':'Zero processed companion frames and no recorded enhancement video. Not an enhancement performance result.'},
        'excluded_intervened_standard_pass':read(ROOT/'runs/sustained-standard-analysis-v2.json'),
        'operational_recovery':recovery,
        'sparse_telemetry_diagnostic':read(ROOT/'runs/sustained-telemetry-diagnostic-v1.json'),
        'driver_retention':'Initial pilot and standard driver copies were retained after their sessions. Later revisions added automatic driver retention, an explicit plan argument, foreground logging and startup guards after the zero-frame failure. All three final controlled passes use the same retained driver and validated 10 Hz addon; model and shader are unchanged.',
        'runtime_binary_limit':'Current diagnostic companion binary is measured with DXGI statistics disabled. Its model, shader and controls are unchanged; the earlier independently verified downloadable package is not rebuilt in this experiment.',
        'appearance_gain_accepted':False,'physical_input_verified':False,'capture_to_display_latency':None,
        'working_package_changed':False,'source_hashes':{p.relative_to(ROOT).as_posix():digest(p) for p in records}}
    files = [(video,'playable-sustained-unretimed.mp4',composed['transformation']),
             (composed_root/'poster.png','playable-sustained-poster.png','Decoded comparison frame requested at 20 seconds; encoded video colors and panel scaling retained.')]
    for name,row in zip(('standard','reduced','neural'),analysis['runs']):
        files.append((review_root/row['run']/'key-020.png',f'sustained-{name}-020.png','Native 2560x1440 decoded frame requested at 20 seconds from its recorded pass. Separate repeats, no image alignment or grading.'))
    from pathlib import PureWindowsPath
    steam_common = PureWindowsPath(valid['argv'][0]).parent.parent.parent.as_posix()
    replacements = [(ROOT.as_posix(), '.'), (steam_common, '<STEAM_COMMON>'),
                    (Path.home().as_posix(), '<USER_HOME>'), ('C:/Windows/Fonts', '<WINDOWS_FONTS>')]
    report['publication_redaction'] = 'Machine roots and profile account identifiers are replaced in the published copy. Original local files and their hashes are retained.'
    publication_copy(report, replacements)  # Check before copying any public media.
    manifest_path = ROOT/'docs/media/manifest.json'; manifest = read(manifest_path)
    report['published_media'] = []
    for path,name,transform in files:
        destination = ROOT/'docs/media'/name
        if destination.exists(): raise FileExistsError(destination)
        is_video = path.suffix == '.mp4'
        entry = {'file':name,'sha256':digest(path),'bytes':path.stat().st_size,'dimensions':[2304,464] if is_video else list(Image.open(path).size),
            'source_record':target.relative_to(ROOT).as_posix(),'source_artifact':path.relative_to(ROOT).as_posix(),
            'source_sha256':digest(path),'transformation':transform,'rights':'Arma Reforger imagery © Bohemia Interactive, outside MIT code license.'}
        if is_video: entry.update(duration_seconds=184,playback_speed=1,retimed=False)
        manifest['videos' if is_video else 'images'].append(entry); report['published_media'].append(entry)
        shutil.copyfile(path,destination)
    public_report = publication_copy(report, replacements)
    write_json(target,public_report); write_json(manifest_path,manifest)
    print(json.dumps({'elapsed_minutes':elapsed,'within_bound':report['within_declared_time_bound'],'motion_and_repeat_gates':analysis['all_motion_and_repeat_gates_pass']}))


if __name__ == '__main__': main()
