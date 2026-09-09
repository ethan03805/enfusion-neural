"""Capture one predeclared camera color-lookup control in an isolated simulation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr import sequence,color_lookup
from enr.references import digest,lab_modules,write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',required=True);p.add_argument('--lab-source',required=True);p.add_argument('--build',required=True)
    p.add_argument('--case',required=True,choices=['off','identity','inversion','constant','removed'])
    a=p.parse_args();out=Path(a.out).resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Choose a new empty lookup capture directory')
    build,copies,provenance=color_lookup.load_build(a.build,ROOT);plan=build['plan']
    initialize,run_workbench,doctor=lab_modules(a.lab_source)
    from enfusion_lab import runner
    initialize(out);config=sequence.load_config(ROOT/plan['capture_base']);config.update(plan['capture_overrides'])
    sequence.prepare(out,config);write_json(out/'capture-config.json',config);write_json(out/'doctor.json',doctor())
    shutil.copyfile(__file__,out/'capture_driver.py')
    assets=out/'addon/Assets/ENR_ColorLookup';assets.mkdir(parents=True)
    for source,name in copies:shutil.copyfile(source,assets/name)
    materials=[]
    for item in build['identities']:
        name=item['case'];guid=hashlib.sha256((provenance['build_report_sha256']+name).encode()).hexdigest()[:16].upper()
        resource='{'+guid+'}Assets/ENR_ColorLookup/'+name+'.emat'
        text='ColorGradingEffect {\n Enabled 1\n ColorTable "'+item['resource']+'"\n}\n'
        (assets/(name+'.emat')).write_bytes(text.encode())
        (assets/(name+'.emat.meta')).write_bytes(('MetaFileClass {\n Name "'+resource+'"\n Configurations {\n  EMATResourceClass PC {\n  }\n }\n}\n').encode())
        materials.append({'case':name,'resource':resource,'table':item['resource'],'sha256':digest(assets/(name+'.emat'))})
    selected=next(v for v in materials if v['case']==('inversion' if a.case=='removed' else 'identity' if a.case=='off' else a.case))
    plugin=ROOT/'adapters/enfusion/probes/ENR_ColorLookup.c';shutil.copyfile(plugin,out/'addon/Scripts/Game'/plugin.name)
    code='#ifdef WORKBENCH\nclass ENR_LookupConfig { static string Case = '+json.dumps(a.case)+'; static string MaterialPath = '+json.dumps(selected['resource'])+'; }\n#endif\n'
    (out/'addon/Scripts/Game/ENR_LookupConfig.c').write_bytes(code.encode())
    capture=out/'addon/Scripts/Game/ELab_GameCapture.c';text=capture.read_text();needle='ENR_Sequence.Camera(world);'
    if text.count(needle)!=1:raise ValueError('Capture entry point changed')
    capture.write_bytes(text.replace(needle,needle+'\n  ENR_ColorLookup.Init(world);').encode())
    with sequence.private_settings(runner):
        validation=run_workbench(out,'validate',timeout=180)
        if validation['status']!='succeeded':raise ValueError('Lookup capture addon did not compile')
        pos,direction=sequence.camera(config,0)
        run=run_workbench(out,'capture',world=config['world'],position=pos,direction=direction,settle=config['settle_seconds'],timeout=config['timeout_seconds'])
    folder=Path(run['directory']);result=sequence.verify(config,run)
    log=(folder/'console.log').read_text(encoding='utf-8')
    records=[line.split('ENR_LOOKUP ',1)[1] for line in log.splitlines() if 'ENR_LOOKUP ' in line]
    expected_requests=['none'] if a.case=='off' else ['apply','remove'] if a.case=='removed' else ['apply']
    if [v.split('=',1)[1] for v in records if v.startswith('requested=')]!=expected_requests or any(v.startswith('failed=') for v in records):
        raise ValueError('Missing or failed lookup requests')
    if len([v for v in records if v.startswith('case=')])!=1:raise ValueError('Duplicate lookup initialization')
    readback=[v for v in records if v.startswith('material_class=')]
    if a.case!='off' and readback!=['material_class=ColorGradingEffect table_read=1 table='+selected['table']+' enabled_read=1 enabled=1']:
        raise ValueError('Native material readback differs')
    result.update(operation='color-lookup-capture',case=a.case,plan_sha256=build['plan_sha256'],build=provenance,materials=materials,
                  selected_material=selected,lookup_records=records,driver_sha256=digest(out/'capture_driver.py'),
                  validation_run=validation['run_id'],validation_manifest_sha256=digest(Path(validation['directory'])/'run.json'),
                  capture_manifest_sha256=digest(folder/'run.json'),console_sha256=digest(folder/'console.log'),
                  config_sha256=digest(out/'capture-config.json'),visual_review='pending',
                  rendered_effect_verified=False,renderer_integration_verified=False,scope=plan['scope'])
    write_json(out/'lookup-capture.json',result)
    print(json.dumps({'status':result['status'],'case':a.case,'run':run['run_id'],'frames':result['frames'],'lookup':records}))


if __name__=='__main__':main()
