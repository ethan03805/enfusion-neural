"""Bounded native VFS reads into an isolated Enfusion Lab profile."""
import argparse
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr import sequence
from enr.references import digest, lab_modules, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--lab-source', required=True)
    a = p.parse_args(); out = a.out.resolve()
    if out.exists() and any(out.iterdir()): raise ValueError('Use a new empty run directory')
    plan_path = ROOT / 'scenes/playable-material-access-v1.json'
    plan = json.loads(plan_path.read_text())
    initialize, run_workbench, doctor = lab_modules(a.lab_source)
    from enfusion_lab import runner
    from enfusion_lab.config import load_project, resolve_installation
    detected = doctor()
    if not detected['workbench_available']: raise ValueError('Workbench unavailable')
    initialize(out); sequence.prepare(out, sequence.load_config(ROOT / 'scenes/arland-motion-v1.json'))
    write_json(out / 'doctor.json', detected)
    config = 'class ENR_AccessConfig { static int Count() { return ' + str(len(plan['files'])) + '; }\n'
    for method, key, prefix in [('Label', 'name', ''), ('Source', 'source', '$ArmaReforger:')]:
        config += ' static string ' + method + '(int index) {\n'
        for i, item in enumerate(plan['files']):
            if not re.fullmatch(r'[A-Za-z0-9_./]+', item[key]) or '..' in item[key]:
                raise ValueError('Invalid declared file')
            config += ' if (index == ' + str(i) + ') return ' + json.dumps(prefix + item[key]) + ';\n'
        config += ' return "";\n }\n'
    config += '}\n'
    scripts = out / 'addon/Scripts/WorkbenchGame'
    (scripts / 'ENR_AccessConfig.c').write_bytes(config.encode())
    plugin = ROOT / 'adapters/enfusion/probes/ENR_MaterialAccessPlugin.c'
    shutil.copyfile(plugin, scripts / plugin.name)
    with sequence.private_settings(runner): validation = run_workbench(out, 'validate', timeout=120)
    if validation['status'] != 'succeeded': raise ValueError('Access plugin did not compile')
    root, project = load_project(out); executable, game = resolve_installation(project)
    folder, record = runner.allocate_run(root, 'material-access')
    argv = [str(executable), '-gproj', str(folder / 'addon/addon.gproj'), '-addonsDir', str(game / 'addons'),
            '-profile', str(folder / 'profile'), '-cfg', str(folder / 'addon/ENR_Engine.conf'),
            '-forceSettings', str(folder / 'addon/ENR_Workbench.ini'), '-diagMenu', str(folder / 'addon/ENR_Diag.txt'),
            '-wbModule=ResourceManager', '-run', '-plugin=ENR_MaterialAccessPlugin']
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
            if code != 0 or text.count('ENR_ACCESS started') != 1 or text.count('ENR_ACCESS completed') != 1:
                raise ValueError('Access callback did not complete naturally')
            for item in plan['files']:
                if len(re.findall('ENR_ACCESS_FILE name=' + re.escape(item['name']) + r' exists=[01] copied=[01]\b', text)) != 1:
                    raise ValueError('Missing or duplicate copy outcome')
            record['status'] = 'succeeded'
        except (OSError, ValueError, subprocess.TimeoutExpired, KeyboardInterrupt) as error:
            record.update(status='failed', error=str(error))
        finally:
            if process is not None:
                record['terminated_owned_process'] = runner.stop_owned(process); record['process_exit_code'] = process.returncode
            text = runner.collect_logs(folder / 'profile'); (folder / 'console.log').write_bytes(text.encode())
            record.update(finished_at=runner.utc_now(), wall_seconds=time.monotonic()-start, console_sha256=digest(folder / 'console.log'))
            write_json(folder / 'run.json', record)
    files = []
    for item in plan['files']:
        found = list((folder / 'profile').rglob('ENR_native_' + item['name']))
        if len(found) > 1: raise ValueError('Ambiguous profile output')
        entry = {**item, 'output_present': bool(found)}
        if found:
            data = found[0].read_bytes()
            entry.update(path=str(found[0].relative_to(out)), bytes=len(data), sha256=digest(found[0]), header_hex=data[:160].hex())
            if len(data) >= 128 and data[:4] == b'DDS ':
                word = lambda offset: struct.unpack_from('<I', data, offset)[0]
                entry['dds_header'] = {'width': word(16), 'height': word(12), 'mips': word(28),
                    'fourcc': data[84:88].decode('ascii', errors='backslashreplace'), 'enfusion_tag': data[36:40].decode('ascii', errors='backslashreplace')}
                if data[84:88] == b'DX10' and len(data) >= 148: entry['dds_header']['dxgi_format'] = word(128)
        files.append(entry)
    result = {'schema_version': 1, 'operation': 'material-access', 'status': record['status'], 'plan': plan,
        'plan_sha256': digest(plan_path), 'run_id': record['run_id'], 'manifest_sha256': digest(folder / 'run.json'),
        'validation_run': validation['run_id'], 'validation_manifest_sha256': digest(Path(validation['directory']) / 'run.json'),
        'driver_sha256': digest(folder / 'driver.py'), 'plugin_sha256': digest(folder / 'addon/Scripts/WorkbenchGame' / plugin.name),
        'console_sha256': record['console_sha256'], 'files': files,
        'records': [line.split('ENR_ACCESS', 1)[1] for line in text.splitlines() if 'ENR_ACCESS' in line],
        'texture_pixels_decoded': False, 'improved_appearance_target': False}
    write_json(out / 'access.json', result)
    print(json.dumps({'status': record['status'], 'run': record['run_id'], 'error': record.get('error'), 'files': files}))
    return 0 if record['status'] == 'succeeded' else 1


if __name__ == '__main__': sys.exit(main())
