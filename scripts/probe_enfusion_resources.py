"""Run a bounded read-only resource inventory through an isolated Lab addon."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr import sequence,image_bridge
from enr.references import lab_modules,write_json,digest


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--lab-source',required=True)
    p.add_argument('--config',default=str(ROOT/'scenes/arland-motion-v1.json'))
    p.add_argument('--world-inventory',help='Prior native inventory that observed an additional world resource')
    p.add_argument('--query',action='append',help='Replace the default resource-search terms; repeat for several bounded searches')
    a=p.parse_args();out=Path(a.out).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Use a new empty inventory directory')
    if a.query and (len(a.query)>8 or any(not re.fullmatch(r'[A-Za-z0-9_ -]{1,48}',q) for q in a.query)):
        raise ValueError('Use at most eight simple resource search terms')
    initialize,run_workbench,doctor=lab_modules(a.lab_source)
    from enfusion_lab import runner
    config,world_binding=image_bridge.load_probe_config(a.config,a.world_inventory)
    initialize(out);config['samples']=1
    sequence.prepare(out,config);write_json(out/'doctor.json',doctor())
    source=ROOT/'adapters/enfusion/probes/ENR_ResourceProbe.c'
    installed=out/'addon/Scripts/WorkbenchGame/ENR_ResourceProbe.c';probe=source.read_text()
    if a.query:
        probe,count=re.subn(r'array<string> queries = \{[^\n]+\};','array<string> queries = {'+', '.join(json.dumps(q) for q in a.query)+'};',probe)
        if count!=1:raise ValueError('Resource query declaration changed')
    installed.write_bytes(probe.encode('utf-8'))
    plugin=out/'addon/Scripts/WorkbenchGame/ELab_CapturePlugin.c'
    content=plugin.read_text();needle='editor.SwitchToGameMode(false, true);'
    if content.count(needle)!=1:raise ValueError('Capture entry point changed')
    content=content.replace(needle,'ENR_ResourceProbe probe = new ENR_ResourceProbe();\n  probe.Run();\n  probe.WorldLocations(editor.GetApi().GetWorld());\n  '+needle)
    plugin.write_text(content)
    with sequence.private_settings(runner):
        validation=run_workbench(out,'validate',timeout=180)
        if validation['status']!='succeeded':raise ValueError('Inventory addon did not compile')
        pos,direction=sequence.camera(config,0)
        run=run_workbench(out,'capture',position=pos,direction=direction,world=config['world'],settle=8,timeout=240)
    directory=Path(run['directory']);lines=(directory/'console.log').read_text(errors='replace').splitlines()
    report={'schema_version':1,'scope':'Read-only resource names/material declarations; no live neural bridge established',
            'validation_run':validation['run_id'],'capture_run':run['run_id'],'status':run['status'],
            'probe_sha256':digest(installed),'template_sha256':digest(source),'queries':a.query,
            'world_binding':world_binding,
            'console_sha256':digest(directory/'console.log'),
            'records':[line for line in lines if 'ENR_RESOURCE' in line or 'ENR_MATERIAL' in line or 'ENR_LOCATION' in line or 'ENR_CORE' in line]}
    write_json(out/'resources.json',report)
    print(json.dumps({'status':report['status'],'records':len(report['records']),'capture':run['image'],'directory':str(directory)},indent=2))


if __name__=='__main__':main()
