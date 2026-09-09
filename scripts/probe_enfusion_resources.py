"""Run a bounded read-only resource inventory through an isolated Lab addon."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr import sequence
from enr.references import lab_modules,write_json,digest


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--lab-source',required=True)
    a=p.parse_args();out=Path(a.out).resolve()
    initialize,run_workbench,doctor=lab_modules(a.lab_source)
    from enfusion_lab import runner
    initialize(out);config=sequence.load_config(ROOT/'scenes/arland-motion-v1.json');config['samples']=1
    sequence.prepare(out,config);write_json(out/'doctor.json',doctor())
    source=ROOT/'adapters/enfusion/probes/ENR_ResourceProbe.c'
    (out/'addon/Scripts/WorkbenchGame/ENR_ResourceProbe.c').write_bytes(source.read_bytes())
    plugin=out/'addon/Scripts/WorkbenchGame/ELab_CapturePlugin.c'
    content=plugin.read_text();needle='editor.SwitchToGameMode(false, true);'
    if content.count(needle)!=1:raise ValueError('Capture entry point changed')
    content=content.replace(needle,'ENR_ResourceProbe probe = new ENR_ResourceProbe();\n  probe.Run();\n  probe.WorldLocations(editor.GetApi().GetWorld());\n  '+needle)
    plugin.write_text(content)
    with sequence.private_settings(runner):
        validation=run_workbench(out,'validate',timeout=180)
        pos,direction=sequence.camera(config,0)
        run=run_workbench(out,'capture',position=pos,direction=direction,world=config['world'],settle=8,timeout=240)
    directory=Path(run['directory']);lines=(directory/'console.log').read_text(errors='replace').splitlines()
    report={'schema_version':1,'scope':'Read-only resource names/material declarations; no live neural bridge established',
            'validation_run':validation['run_id'],'capture_run':run['run_id'],'status':run['status'],
            'probe_sha256':digest(source),'console_sha256':digest(directory/'console.log'),
            'records':[line for line in lines if 'ENR_RESOURCE' in line or 'ENR_MATERIAL' in line or 'ENR_LOCATION' in line or 'ENR_CORE' in line]}
    write_json(out/'resources.json',report)
    print(json.dumps({'status':report['status'],'records':len(report['records']),'capture':run['image'],'directory':str(directory)},indent=2))


if __name__=='__main__':main()
