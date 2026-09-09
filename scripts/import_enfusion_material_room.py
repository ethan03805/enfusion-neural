"""Import the hash-bound original reference FBX in a new isolated Workbench addon.

Successful import does not establish camera/material/light correspondence,
paired appearance data, neural execution or a renderer extension.
"""
import argparse
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr import sequence
from enr.references import digest, lab_modules, write_json


def require_material_sections(text):
    """A valid MeshObject can be empty, as the retained v5 control demonstrates."""
    material_counts = re.findall(r'ENR_IMPORT \{"event":"materials","count":([0-9]+)\}', text)
    if len(material_counts) != 1 or int(material_counts[0]) < 1:
        raise ValueError('Loaded resource has no observed material sections; room import remains unverified')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--source-root', required=True)
    parser.add_argument('--lab-source', required=True)
    parser.add_argument('--timeout-seconds', type=int, default=120, choices=range(30,301))
    parser.add_argument('--route', choices=('generic', 'fbx-handler', 'typed-metadata', 'load-completed', 'handler-completed', 'inspect-metadata', 'build-live'), default='build-live')
    parser.add_argument('--built-import', help='Prior retained import project, required for a completed-resource route')
    parser.add_argument('--derived-root', help='Optional LOD0 export with verified derivation.json')
    args = parser.parse_args()
    evidence_path = ROOT / 'evidence/material-room-v1.json'
    evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
    original = Path(args.source_root) / 'material-room.fbx'
    if digest(original) != evidence['source_artifacts']['fbx_sha256']:
        raise ValueError('FBX differs from the reviewed synthetic reference geometry')
    derivation = None
    if args.derived_root:
        derived_root = Path(args.derived_root).resolve()
        derivation_path = derived_root / 'derivation.json'
        derivation = json.loads(derivation_path.read_text(encoding='utf-8'))
        if (derivation['status'] != 'succeeded' or derivation['operation'] != 'original-room-lod0-export'
                or derivation['original_fbx_sha256'] != digest(original)
                or derivation['source_evidence_sha256'] != digest(evidence_path)
                or derivation['fbx_sha256'] != digest(derived_root / 'material-room.fbx')
                or derivation['mesh_count'] != 12 or not derivation['in_memory_geometry_unchanged']
                or not derivation['topology_and_material_slots_equal']
                or not 0 <= derivation['max_roundtrip_coordinate_error_m'] <= 2e-6):
            raise ValueError('Derived export does not preserve the original room contract')
        original = derived_root / 'material-room.fbx'
        derivation = {'report': derivation, 'report_sha256': digest(derivation_path)}
    completed_assets = []
    prior = None
    if args.route in ('load-completed', 'handler-completed', 'inspect-metadata') or (args.route == 'build-live' and args.built_import):
        if not args.built_import:
            raise ValueError('Completed-resource routes require --built-import')
        prior_root = Path(args.built_import).resolve()
        prior_path = prior_root / 'import.json'
        prior_report = json.loads(prior_path.read_text(encoding='utf-8'))
        prior_run = prior_root / 'runs' / prior_report['run_id']
        if prior_root not in prior_run.resolve().parents:
            raise ValueError('Prior run must stay inside its import project')
        if digest(prior_run / 'run.json') != prior_report['run_manifest_sha256']:
            raise ValueError('Prior import manifest changed')
        if prior_report['source_fbx_sha256'] != digest(original):
            raise ValueError('Prior import uses different source geometry')
        base = prior_run / 'addon/Assets/ENR_ReferenceRoom'
        for asset in prior_report['retained_assets']:
            path = (base / asset['file']).resolve()
            if base.resolve() not in path.parents or digest(path) != asset['sha256']:
                raise ValueError('Prior import asset path or hash mismatch')
            completed_assets.append((path, asset['file']))
        prior = {'run_id': prior_report['run_id'], 'report_sha256': digest(prior_path)}
    elif args.built_import:
        raise ValueError('--built-import requires a completed-resource route')
    initialize, run_workbench, doctor = lab_modules(args.lab_source)
    from enfusion_lab import runner
    from enfusion_lab.config import load_project, resolve_installation
    detected = doctor()
    if not detected['workbench_available']:
        raise ValueError('Stable Workbench unavailable')
    out = Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Use a new empty import project')
    initialize(out)
    project_file = out / 'addon/addon.gproj'
    project_text = project_file.read_text(encoding='utf-8')
    project_file.write_text(project_text.replace('TITLE "Enfusion Lab"', 'TITLE "Enfusion Lab - Reference Import"'), encoding='utf-8')
    sequence.prepare(out, sequence.load_config(ROOT / 'scenes/arland-motion-v1.json'))
    write_json(out / 'doctor.json', detected)
    asset_dir = out / 'addon/Assets/ENR_ReferenceRoom'
    asset_dir.mkdir(parents=True)
    shutil.copyfile(original, asset_dir / original.name)
    for source, name in completed_assets:
        target = asset_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    if args.route == 'typed-metadata' or (args.route == 'build-live' and not args.built_import):
        # Metadata syntax and the standard PC common resource are documented by
        # Bohemia's public sample models. Fresh IDs belong to this original mesh.
        model_guid = uuid.uuid4().hex[:16].upper()
        common_guid = uuid.uuid4().hex[:16].upper()
        metadata = ('MetaFileClass {\n Name "{' + model_guid + '}Assets/ENR_ReferenceRoom/material-room.xob"\n'
                    ' Configurations {\n  FBXResourceClass PC {\n'
                    '   Common TXOCommonClass "{' + common_guid + '}" : "{0877E7C4BB2B2C9A}Configs/System/ResourceTypes/PC/MeshObjectCommon.conf" {\n   }\n'
                    '  }\n }\n}\n')
        (asset_dir / 'material-room.xob.meta').write_bytes(metadata.encode('utf-8'))
    plugin = ROOT / 'adapters/enfusion/probes/ENR_MaterialRoomImportPlugin.c'
    shutil.copyfile(plugin, out / 'addon/Scripts/WorkbenchGame' / plugin.name)
    model = 'Assets/ENR_ReferenceRoom/material-room.xob'
    meta_path = asset_dir / 'material-room.xob.meta'
    if meta_path.exists():
        match = re.search(r'Name "(\{[0-9A-F]{16}\}Assets/ENR_ReferenceRoom/material-room\.xob)"', meta_path.read_text(encoding='utf-8'))
        if not match:
            raise ValueError('Model metadata lacks its expected resource identity')
        model = match.group(1)
    (out / 'addon/Scripts/WorkbenchGame/ENR_ImportConfig.c').write_text(
        'class ENR_ImportConfig { static bool FBXHandler = ' + str(args.route in ('fbx-handler', 'handler-completed')).lower() +
        '; static bool TypedMetadata = ' + str(args.route == 'typed-metadata').lower() +
        '; static bool LoadCompleted = ' + str(args.route == 'load-completed').lower() +
        '; static bool InspectMetadata = ' + str(args.route == 'inspect-metadata').lower() +
        '; static bool BuildLive = ' + str(args.route == 'build-live').lower() +
        '; static ResourceName Model = "' + model + '"; }\n', encoding='utf-8')
    with sequence.private_settings(runner):
        validation = run_workbench(out, 'validate', timeout=180)
    if validation['status'] != 'succeeded':
        raise ValueError('Import addon failed validation')
    root, config = load_project(out)
    executable, game = resolve_installation(config)
    operation = 'original-room-metadata' if args.route == 'inspect-metadata' else 'original-room-import'
    scope = ('Read-only inspection of original-room import metadata; no import or rendering verification'
             if args.route == 'inspect-metadata' else 'Original mesh registration/import only; visual and appearance correspondence unverified')
    if args.route == 'build-live':
        operation = 'original-room-build-observation'
        scope = 'Observe asynchronous rebuild while the private editor remains alive; subsequent resource load and geometry checks required'
    run_dir, record = runner.allocate_run(root, operation)
    argv = [str(executable), '-gproj', str(run_dir / 'addon/addon.gproj'),
            '-addonsDir', str(game / 'addons'), '-profile', str(run_dir / 'profile'),
            '-cfg', str(run_dir / 'addon/ENR_Engine.conf'),
            '-forceSettings', str(run_dir / 'addon/ENR_Workbench.ini'),
            '-diagMenu', str(run_dir / 'addon/ENR_Diag.txt'),
            '-wbModule=ResourceManager', '-run', '-plugin=ENR_MaterialRoomImportPlugin']
    record.update(argv=argv, timeout_seconds=args.timeout_seconds, world=None, capture_mode=None,
                  validation_run=validation['run_id'], script_sha256=digest(__file__),
                  source_fbx_sha256=digest(original), source_evidence_sha256=digest(evidence_path),
                  scope=scope)
    record['route'] = args.route
    record['prior_import'] = prior
    record['derivation'] = derivation
    process = None
    with runner.project_lock(root):
        run_dir.mkdir(parents=True)
        profile = run_dir / 'profile'; profile.mkdir()
        record['addon_sha256'] = runner.snapshot_addon(root / 'addon', run_dir / 'addon')
        (run_dir / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
        record.update(status='running', started_at=runner.utc_now())
        write_json(run_dir / 'run.json', record)
        start = time.monotonic()
        try:
            with (run_dir / 'process.log').open('wb') as log:
                startup = subprocess.STARTUPINFO()
                startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup.wShowWindow = subprocess.SW_HIDE
                process = subprocess.Popen(argv, cwd=run_dir, stdout=log, stderr=subprocess.STDOUT,
                                           stdin=subprocess.DEVNULL, shell=False, startupinfo=startup)
                record['pid'] = process.pid
                write_json(run_dir / 'run.json', record)
                if args.route == 'build-live':
                    observed_at = None
                    while time.monotonic() - start < args.timeout_seconds:
                        live_text = runner.collect_logs(profile)
                        requested = 'ENR_IMPORT {"event":"live_build_requested"}' in live_text
                        if requested and observed_at is None:
                            observed_at = time.monotonic()
                        if observed_at is not None and time.monotonic() - observed_at >= 10:
                            break
                        if process.poll() is not None:
                            break
                        time.sleep(0.2)
                    record['alive_after_build_observation'] = process.poll() is None
                    record['build_observation_seconds'] = time.monotonic() - observed_at if observed_at else None
                    code = process.poll()
                else:
                    code = process.wait(timeout=args.timeout_seconds)
            text = runner.collect_logs(profile)
            if args.route == 'build-live':
                if (text.count('ENR_IMPORT {"event":"live_build_requested"}') != 1
                        or 'Build successful' not in text or not record['alive_after_build_observation']):
                    raise ValueError('Did not observe a completed rebuild while the editor remained alive')
            elif code != 0 or text.count('ENR_IMPORT {"event":"started"}') != 1 or text.count('ENR_IMPORT {"event":"completed"}') != 1:
                raise ValueError('Import did not exit naturally with one native completion')
            imported = run_dir / 'addon/Assets/ENR_ReferenceRoom'
            if not (imported / 'material-room.xob').is_file() or not (imported / 'material-room.xob.meta').is_file():
                raise ValueError('Native completion did not produce model and import metadata')
            if digest(imported / original.name) != digest(original):
                raise ValueError('Original FBX changed during import')
            if args.route == 'build-live':
                if (imported / 'material-room.xob').stat().st_size <= 80:
                    raise ValueError('Editor stayed alive but the output remains a header-only resource')
            elif args.route == 'inspect-metadata':
                if text.count('ENR_IMPORT {"event":"metadata_inspected","configurations":1}') != 1:
                    raise ValueError('Metadata inspection did not observe one PC configuration')
            else:
                require_material_sections(text)
            record['status'] = 'succeeded'
        except subprocess.TimeoutExpired:
            record.update(status='failed', error='Workbench original-room import timed out after ' + str(args.timeout_seconds) + ' seconds')
        except (OSError, ValueError, KeyboardInterrupt) as error:
            record.update(status='failed', error=str(error))
        finally:
            if process is not None:
                record['terminated_owned_process'] = runner.stop_owned(process)
                record['process_exit_code'] = process.returncode
            text = runner.collect_logs(profile)
            (run_dir / 'console.log').write_bytes(text.encode('utf-8'))
            imported = run_dir / 'addon/Assets/ENR_ReferenceRoom'
            record['retained_assets'] = [{'file': p.relative_to(imported).as_posix(),
                                           'bytes': p.stat().st_size, 'sha256': digest(p)}
                                          for p in sorted(imported.rglob('*')) if p.is_file()]
            record.update(finished_at=runner.utc_now(), wall_seconds=time.monotonic() - start,
                          console_sha256=digest(run_dir / 'console.log'))
            write_json(run_dir / 'run.json', record)
    report = {'schema_version': 1, 'status': record['status'], 'operation': operation,
              'run_id': record['run_id'], 'run_manifest_sha256': digest(run_dir / 'run.json'),
              'validation_run': validation['run_id'],
              'validation_manifest_sha256': digest(Path(validation['directory']) / 'run.json'),
              'source_fbx_sha256': record['source_fbx_sha256'],
              'source_evidence_sha256': record['source_evidence_sha256'],
              'route': args.route,
              'prior_import': prior,
              'derivation': derivation,
              'plugin_sha256': digest(run_dir / 'addon/Scripts/WorkbenchGame' / plugin.name),
              'console_sha256': record['console_sha256'],
              'retained_assets': record['retained_assets'],
              'native_records': [line.split('ENR_IMPORT ', 1)[1] for line in text.splitlines() if 'ENR_IMPORT ' in line],
              'metadata_records': [line.split('ENR_META_', 1)[1] for line in text.splitlines() if 'ENR_META_' in line],
              'scope': record['scope'], 'visual_review': 'pending',
              'engine_geometry_verified': False,
              'aligned_appearance_pair_verified': False, 'renderer_integration_verified': False}
    write_json(out / 'import.json', report)
    print(json.dumps({'status': record['status'], 'run': record['run_id'],
                      'asset_count': len(record['retained_assets']), 'error': record.get('error')}, indent=2))
    return 0 if record['status'] == 'succeeded' else 1


if __name__ == '__main__':
    sys.exit(main())
