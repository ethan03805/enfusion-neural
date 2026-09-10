"""Verify every archived byte, the tested binary and the unchanged launcher."""
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr.references import digest,write_json

def main():
    name='Enfusion-Neural-Playable-2026-09-10-Guarded'
    archive=ROOT/'runs/deliverables'/(name+'.zip')
    out=ROOT/'runs/guarded-package-audit-v1'; out.mkdir(exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            p=Path(item.filename)
            if p.is_absolute() or '..' in p.parts or p.parts[0]!=name:
                raise ValueError('Unexpected archive member')
        if z.testzip() is not None: raise ValueError('Archive CRC failure')
        z.extractall(out)
    package=out/name
    manifest=json.loads((package/'manifest.json').read_text())
    for rel,sha in manifest['files'].items():
        if digest(package/rel)!=sha: raise ValueError('Archive hash mismatch: '+rel)
    plan=json.loads((ROOT/'scenes/playable-live-guard-v1.json').read_text())
    for rel in ['build/Release/enr_companion.exe','native/companion.cpp','native/curve_network.h']:
        if digest(package/rel)!=plan['processing_hashes'][rel]: raise ValueError('Package differs from live build')
    if digest(package/'models/zero-dce-plusplus/weights.bin')!=plan['processing_hashes']['runs/pretrained/zero-dce-plusplus/weights.bin']:
        raise ValueError('Package checkpoint differs')
    for rel in ['scripts/play.py','scripts/launch_playable.py','Start-Playable.cmd']:
        if digest(package/rel)!=digest(ROOT/rel): raise ValueError('Changed launcher')
    sources=re.findall(r'add_executable\(\w+\s+([^\)]+)\)',(package/'native/CMakeLists.txt').read_text())
    for source in sources:
        if not (package/'native'/source.strip()).is_file(): raise ValueError('Missing build source')
    help_run=subprocess.run(['powershell','-NoProfile','-Command',"& './Start-Playable.cmd' --help"],cwd=package,text=True,capture_output=True,timeout=30)
    (out/'launcher-help.log').write_text(help_run.stdout+help_run.stderr)
    if help_run.returncode or '--viewer' not in help_run.stdout: raise ValueError('Packaged launcher help failed')
    report={'schema_version':1,'status':'passed','download_file':'playable-pipeline-2026-09-10-guarded.zip',
            'sha256':digest(archive),'bytes':archive.stat().st_size,'package_manifest':manifest,'verified_file_count':len(manifest['files']),
            'archive_crc_pass':True,'tested_native_binary_exact':True,'all_cmake_target_sources_present':True,
            'launcher_help_exit_code':help_run.returncode,'launcher_help_sha256':digest(out/'launcher-help.log'),
            'live_evaluation':'evidence/playable-live-guard-v1.json','live_evaluation_sha256':digest(ROOT/'runs/live-guard-v1/evaluation.json'),
            'launch_scope':'Extracted Start-Playable.cmd --help succeeds; launcher and addon are unchanged. This exact archived native executable, shader and weights passed the private live route and controls immediately before packaging. No second extracted-package game benchmark or physical input claim.',
            'previous_package_preserved':'playable-pipeline-2026-09-10.zip','previous_sha256':digest(ROOT/'docs/downloads/playable-pipeline-2026-09-10.zip')}
    write_json(out/'report.json',report)
    print(json.dumps({'status':report['status'],'verified_files':report['verified_file_count'],'sha256':report['sha256']}))

if __name__=='__main__': main()
