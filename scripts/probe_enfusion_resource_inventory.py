"""Compile and run a bounded ScriptEditor resource inventory without a world.

This distinct operation reuses Lab discovery, initialization, validation,
snapshot/lock/log helpers and owned-process cleanup. It never labels inventory
completion as a successful image capture or renderer integration.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr import sequence
from enr.references import digest, lab_modules, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--lab-source', required=True)
    parser.add_argument('--query', action='append', required=True)
    args = parser.parse_args()
    if len(args.query) > 8 or any(not re.fullmatch(r'[A-Za-z0-9_ -]{1,48}', q) for q in args.query):
        raise ValueError('Use at most eight simple resource search terms')
    if len(set(args.query)) != len(args.query):
        raise ValueError('Queries must be distinct')
    initialize, run_workbench, doctor = lab_modules(args.lab_source)
    from enfusion_lab import runner
    from enfusion_lab.config import load_project, resolve_installation
    detected = doctor()
    if not detected['workbench_available']:
        raise ValueError('Stable Workbench is unavailable')
    out = Path(args.out).resolve()
    initialize(out)
    sequence.prepare(out, sequence.load_config(ROOT / 'scenes/arland-motion-v1.json'))
    write_json(out / 'doctor.json', detected)
    directory = out / 'addon/Scripts/WorkbenchGame'
    source = ROOT / 'adapters/enfusion/probes/ENR_ResourceProbe.c'
    probe, count = re.subn(r'array<string> queries = \{[^\n]+\};',
                          'array<string> queries = {' + ', '.join(json.dumps(q) for q in args.query) + '};',
                          source.read_text())
    if count != 1:
        raise ValueError('Resource query declaration changed')
    (directory / source.name).write_bytes(probe.encode('utf-8'))
    plugin = ROOT / 'adapters/enfusion/probes/ENR_ResourceInventoryPlugin.c'
    (directory / plugin.name).write_bytes(plugin.read_bytes())
    with sequence.private_settings(runner):
        validation = run_workbench(out, 'validate', timeout=180)
    if validation['status'] != 'succeeded':
        raise ValueError('Inventory scripts did not compile')
    root, config = load_project(out)
    executable, game = resolve_installation(config)
    run_dir, record = runner.allocate_run(root, 'resource-inventory')
    argv = [str(executable), '-gproj', str(run_dir / 'addon/addon.gproj'),
            '-addonsDir', str(game / 'addons'), '-profile', str(run_dir / 'profile'),
            '-cfg', str(run_dir / 'addon/ENR_Engine.conf'),
            '-forceSettings', str(run_dir / 'addon/ENR_Workbench.ini'),
            '-diagMenu', str(run_dir / 'addon/ENR_Diag.txt'),
            '-wbsilent', '-wbModule=ScriptEditor', '-run', '-plugin=ENR_ResourceInventoryPlugin']
    record.update(argv=argv, queries=args.query, timeout_seconds=45,
                  validation_run=validation['run_id'], world=None, capture_mode=None,
                  script_sha256=digest(Path(__file__)), scope='Resource names only; no world or image capture')
    process = None
    with runner.project_lock(root):
        run_dir.mkdir(parents=True)
        profile = run_dir / 'profile'
        profile.mkdir()
        record['addon_sha256'] = runner.snapshot_addon(root / 'addon', run_dir / 'addon')
        record.update(status='running', started_at=runner.utc_now())
        write_json(run_dir / 'run.json', record)
        start = time.monotonic()
        try:
            with (run_dir / 'process.log').open('wb') as log:
                process = subprocess.Popen(argv, cwd=run_dir, stdout=log, stderr=subprocess.STDOUT,
                                           stdin=subprocess.DEVNULL, shell=False)
                record['pid'] = process.pid
                write_json(run_dir / 'run.json', record)
                code = process.wait(timeout=45)
            text = runner.collect_logs(profile)
            started = text.count('ENR_INVENTORY {"event":"started"}')
            completed = text.count('ENR_INVENTORY {"event":"completed"}')
            if code != 0 or started != 1 or completed != 1:
                raise ValueError('Inventory did not exit naturally with exactly one completion')
            for query in args.query:
                matches = re.findall(r'ENR_RESOURCE_DONE query=' + re.escape(query) + r' count=(\d+) success=(\d+)', text)
                if len(matches) != 1 or matches[0][1] != '1':
                    raise ValueError('Missing or failed resource query: ' + query)
            record['status'] = 'succeeded'
        except (OSError, ValueError, subprocess.TimeoutExpired, KeyboardInterrupt) as error:
            record.update(status='failed', error=str(error))
        finally:
            if process is not None:
                record['terminated_owned_process'] = runner.stop_owned(process)
                record['process_exit_code'] = process.returncode
            text = runner.collect_logs(profile)
            (run_dir / 'console.log').write_bytes(text.encode('utf-8'))
            record.update(finished_at=runner.utc_now(), wall_seconds=time.monotonic() - start,
                          console_sha256=digest(run_dir / 'console.log'))
            write_json(run_dir / 'run.json', record)
    report = {'schema_version': 1, 'status': record['status'], 'operation': 'resource-inventory',
              'inventory_run': record['run_id'], 'validation_run': validation['run_id'],
              'inventory_manifest_sha256': digest(run_dir / 'run.json'),
              'validation_manifest_sha256': digest(Path(validation['directory']) / 'run.json'),
              'console_sha256': record['console_sha256'], 'queries': args.query,
              'probe_sha256': digest(run_dir / 'addon/Scripts/WorkbenchGame/ENR_ResourceProbe.c'),
              'plugin_sha256': digest(run_dir / 'addon/Scripts/WorkbenchGame/ENR_ResourceInventoryPlugin.c'),
              'scope': record['scope'],
              'records': [line for line in text.splitlines() if 'ENR_RESOURCE' in line]}
    write_json(out / 'resources.json', report)
    print(json.dumps({'status': record['status'], 'run': record['run_id'],
                      'records': len(report['records']), 'error': record.get('error')}, indent=2))
    return 0 if record['status'] == 'succeeded' else 1


if __name__ == '__main__':
    sys.exit(main())
