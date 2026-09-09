"""Inspect declared original and previously observed native material containers."""
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


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def verified_inventory(path):
    path = Path(path).resolve(); report = read(path)
    if report['status'] != 'succeeded' or report['operation'] != 'resource-inventory':
        raise ValueError('A completed resource inventory is required')
    for key, command, hash_key in [('inventory_run', 'resource-inventory', 'inventory_manifest_sha256'),
                                   ('validation_run', 'validate', 'validation_manifest_sha256')]:
        name = report[key]
        if not re.fullmatch(r'[0-9]{8}T[0-9]{6}-[a-f0-9]{10}', name):
            raise ValueError('Invalid inventory run name')
        manifest = path.parent / 'runs' / name / 'run.json'; run = read(manifest)
        if digest(manifest) != report[hash_key] or run['status'] != 'succeeded' or run['command'] != command:
            raise ValueError('Inventory provenance differs')
        if key == 'inventory_run' and (run['process_exit_code'] != 0 or run['terminated_owned_process']):
            raise ValueError('Inventory did not exit naturally')
    folder = path.parent / 'runs' / report['inventory_run']
    for name, key in [('console.log', 'console_sha256'),
                      ('addon/Scripts/WorkbenchGame/ENR_ResourceProbe.c', 'probe_sha256'),
                      ('addon/Scripts/WorkbenchGame/ENR_ResourceInventoryPlugin.c', 'plugin_sha256')]:
        if digest(folder / name) != report[key]:
            raise ValueError('Inventory snapshot differs')
    text = (folder / 'console.log').read_text(encoding='utf-8')
    if any(text.count('ENR_INVENTORY ' + json.dumps({'event': event}, separators=(',', ':'))) != 1 for event in ['started', 'completed']):
        raise ValueError('Inventory callback incomplete')
    observed = set(re.findall(r'ENR_RESOURCE query=\S+ resource=(\{[0-9A-F]{16}\}[A-Za-z0-9_./-]+\.emat)(?=\s)', text))
    return observed, {'report_sha256': digest(path), 'run_id': report['inventory_run'],
                      'console_sha256': report['console_sha256'], 'manifest_sha256': report['inventory_manifest_sha256']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True); p.add_argument('--lab-source', required=True)
    p.add_argument('--inventory', required=True)
    a = p.parse_args(); out = Path(a.out).resolve()
    if out.exists() and any(out.iterdir()): raise ValueError('Choose a new empty schema directory')
    plan_path = ROOT / 'scenes/color-lookup-schema-v1.json'; plan = read(plan_path)
    observed, binding = verified_inventory(a.inventory)
    for item in plan['materials']:
        if 'resource' in item and item['resource'] not in observed:
            raise ValueError('Requested material was not observed in native inventory')
        if 'class' in item and item['class'] not in ['ColorGradingEffect', 'ColorsEffect']:
            raise ValueError('Only the declared original effect classes are allowed')
        if not re.fullmatch('[a-z_]+', item['name']): raise ValueError('Invalid material label')
    initialize, run_workbench, doctor = lab_modules(a.lab_source)
    from enfusion_lab import runner
    from enfusion_lab.config import load_project, resolve_installation
    detected = doctor()
    if not detected['workbench_available']: raise ValueError('Workbench unavailable')
    initialize(out); sequence.prepare(out, sequence.load_config(ROOT / 'scenes/arland-motion-v1.json'))
    write_json(out / 'doctor.json', detected)
    assets = out / 'addon/Assets/ENR_Schema'; assets.mkdir(parents=True)
    identities = []
    for item in plan['materials']:
        resource = item.get('resource')
        if 'class' in item:
            filename = item['name'] + '.emat'
            resource = '{' + uuid.uuid4().hex[:16].upper() + '}Assets/ENR_Schema/' + filename
            (assets / filename).write_bytes((item['class'] + ' {\n}\n').encode())
            (assets / (filename + '.meta')).write_bytes(('MetaFileClass {\n Name "' + resource + '"\n Configurations {\n  EMATResourceClass PC {\n  }\n }\n}\n').encode())
        identities.append({**item, 'resource': resource})
    config = 'class ENR_SchemaConfig { static int Count() { return ' + str(len(identities)) + '; }\n'
    for method, key in [('Label', 'name'), ('ResourceAt', 'resource')]:
        config += ' static string ' + method + '(int index) {\n'
        for i, item in enumerate(identities): config += ' if (index == ' + str(i) + ') return ' + json.dumps(item[key]) + ';\n'
        config += ' return "";\n }\n'
    config += '}\n'
    scripts = out / 'addon/Scripts/WorkbenchGame'
    (scripts / 'ENR_SchemaConfig.c').write_bytes(config.encode())
    plugin = ROOT / 'adapters/enfusion/probes/ENR_MaterialSchemaPlugin.c'
    shutil.copyfile(plugin, scripts / plugin.name)
    with sequence.private_settings(runner): validation = run_workbench(out, 'validate', timeout=180)
    if validation['status'] != 'succeeded': raise ValueError('Schema plugin did not compile')
    root, config = load_project(out); executable, game = resolve_installation(config)
    folder, record = runner.allocate_run(root, 'material-schema')
    argv = [str(executable), '-gproj', str(folder / 'addon/addon.gproj'), '-addonsDir', str(game / 'addons'),
            '-profile', str(folder / 'profile'), '-cfg', str(folder / 'addon/ENR_Engine.conf'),
            '-forceSettings', str(folder / 'addon/ENR_Workbench.ini'), '-diagMenu', str(folder / 'addon/ENR_Diag.txt'),
            '-wbModule=ResourceManager', '-run', '-plugin=ENR_MaterialSchemaPlugin']
    record.update(argv=argv, scope=plan['scope'], timeout_seconds=60, validation_run=validation['run_id'])
    process = None
    with runner.project_lock(root):
        folder.mkdir(parents=True); (folder / 'profile').mkdir()
        record['addon_sha256'] = runner.snapshot_addon(out / 'addon', folder / 'addon')
        shutil.copyfile(__file__, folder / 'driver.py')
        record.update(status='running', started_at=runner.utc_now()); write_json(folder / 'run.json', record)
        start = time.monotonic()
        try:
            with (folder / 'process.log').open('wb') as log:
                startup = subprocess.STARTUPINFO(); startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startup.wShowWindow = subprocess.SW_HIDE
                process = subprocess.Popen(argv, cwd=folder, stdout=log, stderr=subprocess.STDOUT,
                                           stdin=subprocess.DEVNULL, shell=False, startupinfo=startup)
                record['pid'] = process.pid; write_json(folder / 'run.json', record)
                code = process.wait(timeout=60)
            text = runner.collect_logs(folder / 'profile')
            if code != 0 or text.count('ENR_SCHEMA started') != 1 or text.count('ENR_SCHEMA completed') != 1:
                raise ValueError('Schema callback did not complete naturally')
            for item in identities:
                if len(re.findall('ENR_SCHEMA_RESULT name=' + item['name'] + r' loaded=[01]\b', text)) != 1:
                    raise ValueError('Missing or duplicate material outcome')
            record['status'] = 'succeeded'
        except (OSError, ValueError, subprocess.TimeoutExpired, KeyboardInterrupt) as error:
            record.update(status='failed', error=str(error))
        finally:
            if process is not None:
                record['terminated_owned_process'] = runner.stop_owned(process); record['process_exit_code'] = process.returncode
            text = runner.collect_logs(folder / 'profile'); (folder / 'console.log').write_bytes(text.encode())
            record.update(finished_at=runner.utc_now(), wall_seconds=time.monotonic()-start, console_sha256=digest(folder / 'console.log'))
            write_json(folder / 'run.json', record)
    result = {'schema_version': 1, 'operation': 'material-schema', 'status': record['status'], 'plan': plan,
              'plan_sha256': digest(plan_path), 'inventory': binding, 'materials': identities,
              'run_id': record['run_id'], 'manifest_sha256': digest(folder / 'run.json'),
              'validation_run': validation['run_id'], 'validation_manifest_sha256': digest(Path(validation['directory']) / 'run.json'),
              'driver_sha256': digest(folder / 'driver.py'), 'plugin_sha256': digest(folder / 'addon/Scripts/WorkbenchGame' / plugin.name),
              'console_sha256': record['console_sha256'], 'records': [line.split('ENR_SCHEMA', 1)[1] for line in text.splitlines() if 'ENR_SCHEMA' in line],
              'renderer_integration': False, 'scope': plan['scope']}
    write_json(out / 'schema.json', result)
    print(json.dumps({'status': record['status'], 'run': record['run_id'], 'error': record.get('error'),
                      'outcomes': [line for line in result['records'] if line.startswith('_RESULT')]}))
    return 0 if record['status'] == 'succeeded' else 1


if __name__ == '__main__': sys.exit(main())
