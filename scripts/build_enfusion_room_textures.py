"""Build hash-bound original TIFF controls in a private Workbench addon."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr import sequence
from enr.references import digest, lab_modules, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--lab-source', required=True)
    parser.add_argument('--timeout-seconds', type=int, default=120, choices=range(30, 301))
    args = parser.parse_args()
    source_root = Path(args.source_root).resolve()
    source_path = source_root / 'textures.json'
    source = json.loads(source_path.read_text(encoding='utf-8'))
    plan_path = ROOT / 'scenes/material-room-texture-control-v1.json'
    if (source['status'] != 'succeeded' or source['operation'] != 'original-room-packed-texture-generation'
            or source['plan_sha256'] != digest(plan_path) or source['generator_sha256'] != digest(source_root / 'generator.py')
            or source['source_scene_sha256'] != digest(ROOT / source['plan']['source_scene'])
            or len(source['textures']) != 18):
        raise ValueError('Texture source provenance differs')
    for texture in source['textures']:
        if not re.fullmatch(r'[a-z_]+_(BCR|NMO)', texture['name']) or texture['file'] != texture['name'] + '.tif':
            raise ValueError('Unexpected original texture name')
        if digest(source_root / texture['file']) != texture['sha256']:
            raise ValueError('Original texture changed')
    out = Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Choose a new empty texture build directory')
    initialize, run_workbench, doctor = lab_modules(args.lab_source)
    from enfusion_lab import runner
    from enfusion_lab.config import load_project, resolve_installation
    detected = doctor()
    if not detected['workbench_available']:
        raise ValueError('Workbench unavailable')
    initialize(out)
    write_json(out / 'doctor.json', detected)
    sequence.prepare(out, sequence.load_config(ROOT / 'scenes/arland-motion-v1.json'))
    asset_relative = 'Assets/ENR_OriginalTextures'
    asset_dir = out / 'addon' / asset_relative
    asset_dir.mkdir(parents=True)
    identities = []
    for texture in source['textures']:
        name = texture['name']
        shutil.copyfile(source_root / texture['file'], asset_dir / texture['file'])
        resource = '{' + uuid.uuid4().hex[:16].upper() + '}' + asset_relative + '/' + name + '.edds'
        space = texture['color_space']
        if space not in ('ToSRGB', 'ToLinear'):
            raise ValueError('Unexpected texture color space')
        metadata = ('MetaFileClass {\n Name "' + resource + '"\n Configurations {\n  TIFFResourceClass PC {\n'
                    '   SourceFile "' + texture['file'] + '"\n   Conversion ColorHQCompression\n'
                    '   ColorSpace ' + space + '\n   GenerateMips 1\n  }\n }\n}\n')
        (asset_dir / (name + '.edds.meta')).write_bytes(metadata.encode('utf-8'))
        identities.append({'name': name, 'resource': resource, 'source': texture['file'],
                           'source_sha256': texture['sha256'], 'color_space': space})
    config = 'class ENR_TextureConfig { static int Count() { return ' + str(len(identities)) + '; }\n static string Source(int index) {\n'
    for index, texture in enumerate(identities):
        config += ' if (index == ' + str(index) + ') return "' + asset_relative + '/' + texture['source'] + '";\n'
    config += ' return "";\n }\n}\n'
    (out / 'addon/Scripts/WorkbenchGame/ENR_TextureConfig.c').write_bytes(config.encode('utf-8'))
    plugin = ROOT / 'adapters/enfusion/probes/ENR_TextureBuildPlugin.c'
    shutil.copyfile(plugin, out / 'addon/Scripts/WorkbenchGame' / plugin.name)
    with sequence.private_settings(runner):
        validation = run_workbench(out, 'validate', timeout=180)
    if validation['status'] != 'succeeded':
        raise ValueError('Texture addon compile failed')
    root, lab_config = load_project(out)
    executable, game = resolve_installation(lab_config)
    directory, record = runner.allocate_run(root, 'original-texture-build')
    argv = [str(executable), '-gproj', str(directory / 'addon/addon.gproj'), '-addonsDir', str(game / 'addons'),
            '-profile', str(directory / 'profile'), '-cfg', str(directory / 'addon/ENR_Engine.conf'),
            '-forceSettings', str(directory / 'addon/ENR_Workbench.ini'), '-diagMenu', str(directory / 'addon/ENR_Diag.txt'),
            '-wbModule=ResourceManager', '-run', '-plugin=ENR_TextureBuildPlugin']
    record.update(argv=argv, validation_run=validation['run_id'], timeout_seconds=args.timeout_seconds,
                  source_report_sha256=digest(source_path), identities=identities,
                  scope='Asynchronous original TIFF build observation; rendered texture response unverified')
    process = None
    with runner.project_lock(root):
        directory.mkdir(parents=True)
        profile = directory / 'profile'
        profile.mkdir()
        record['addon_sha256'] = runner.snapshot_addon(root / 'addon', directory / 'addon')
        shutil.copyfile(__file__, directory / 'driver.py')
        record.update(status='running', started_at=runner.utc_now())
        write_json(directory / 'run.json', record)
        started = time.monotonic()
        try:
            with (directory / 'process.log').open('wb') as output:
                startup = subprocess.STARTUPINFO()
                startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup.wShowWindow = subprocess.SW_HIDE
                process = subprocess.Popen(argv, cwd=directory, stdout=output, stderr=subprocess.STDOUT,
                                           stdin=subprocess.DEVNULL, shell=False, startupinfo=startup)
                record['pid'] = process.pid
                write_json(directory / 'run.json', record)
                ready_at = None
                previous = None
                while time.monotonic() - started < args.timeout_seconds:
                    text = runner.collect_logs(profile)
                    paths = [directory / 'addon' / asset_relative / (item['name'] + '.edds') for item in identities]
                    fingerprint = [(p.stat().st_size, p.stat().st_mtime_ns) if p.exists() else None for p in paths]
                    ready = (text.count('Build successful') >= len(identities) and 'ENR_TEXTURE queued=18' in text
                             and all(item is not None and item[0] > 148 for item in fingerprint))
                    if ready and fingerprint == previous:
                        if ready_at is None:
                            ready_at = time.monotonic()
                        if time.monotonic() - ready_at >= 10:
                            break
                    else:
                        ready_at = None
                    previous = fingerprint
                    if process.poll() is not None:
                        break
                    time.sleep(0.25)
                record['alive_after_build_observation'] = process.poll() is None
                record['stable_output_observation_seconds'] = time.monotonic() - ready_at if ready_at else None
                if not record['alive_after_build_observation'] or ready_at is None or record['stable_output_observation_seconds'] < 10:
                    raise ValueError('All eighteen stable texture builds were not observed before timeout/exit')
                record['status'] = 'succeeded'
        except (OSError, ValueError, KeyboardInterrupt) as error:
            record.update(status='failed', error=str(error))
        finally:
            if process is not None:
                record['terminated_owned_process'] = runner.stop_owned(process)
                record['process_exit_code'] = process.returncode
            text = runner.collect_logs(profile)
            (directory / 'console.log').write_bytes(text.encode('utf-8'))
            assets = directory / 'addon' / asset_relative
            record['retained_assets'] = [{'file': p.relative_to(assets).as_posix(), 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in sorted(assets.rglob('*')) if p.is_file()]
            record.update(finished_at=runner.utc_now(), wall_seconds=time.monotonic()-started,
                          console_sha256=digest(directory / 'console.log'))
            write_json(directory / 'run.json', record)
    report = {'schema_version': 1, 'operation': 'original-texture-build', 'status': record['status'],
              'run_id': record['run_id'], 'run_manifest_sha256': digest(directory / 'run.json'),
              'validation_run': validation['run_id'], 'validation_manifest_sha256': digest(Path(validation['directory']) / 'run.json'),
              'source_report_sha256': digest(source_path), 'source': source, 'identities': identities,
              'driver_sha256': digest(directory / 'driver.py'), 'plugin_sha256': digest(directory / 'addon/Scripts/WorkbenchGame' / plugin.name),
              'console_sha256': record['console_sha256'], 'retained_assets': record['retained_assets'],
              'native_records': [line.split('ENR_TEXTURE ', 1)[1] for line in text.splitlines() if 'ENR_TEXTURE ' in line],
              'error': record.get('error'), 'rendered_response_verified': False}
    write_json(out / 'build.json', report)
    print(json.dumps({'status': report['status'], 'run': report['run_id'], 'retained_assets': len(report['retained_assets']), 'error': report['error']}))
    return 0 if report['status'] == 'succeeded' else 1


if __name__ == '__main__':
    sys.exit(main())
