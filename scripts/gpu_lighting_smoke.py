"""Check all locked lighting variants at odd, HD and 4K sizes without training."""
import argparse
import json
from pathlib import Path
import sys

from lighting_gpu_run import ROOT,locked_models,run,write
from enr import diversity,lighting_gpu
from enr.references import digest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',required=True);p.add_argument('--exe',default='build/Release/enr_gpu.exe')
    p.add_argument('--allow-no-gpu',action='store_true')
    a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    models,binding=locked_models();plan=binding['plan']
    report={'schema_version':1,'status':'running',**binding,'driver_sha256':digest(__file__),
            'invocation_code_sha256':digest(ROOT/'scripts/lighting_gpu_run.py'),
            'gpu_contract_sha256':digest(ROOT/'enr/lighting_gpu.py'),'cpu_reference_sha256':digest(ROOT/'enr/lighting.py'),
            'native_source_sha256':digest(ROOT/'native/enr_gpu.cpp'),'runs':[],'training_performed':False}
    def save():write(out/'run.json',report)
    save()
    try:
        for w,h in plan['smoke_dimensions']:
            x,rgb,alpha,valid=lighting_gpu.fixture(w,h,plan['fixture_seed']+w+h)
            for variant,model in models.items():
                name=f'{variant}-{w}x{h}';print('Starting '+name,flush=True)
                records=lighting_gpu.pack(diversity.select(x,variant),rgb,alpha,valid)
                result=run(out/name,a.exe,records,model,binding['models'][variant],plan['limits'],allow_no_gpu=a.allow_no_gpu)
                report['runs'].append({'id':name,'variant':variant,'kind':'smoke','report_sha256':digest(out/name/'run.json'),**result});save()
                if result['status']=='skipped':report['status']='skipped';return
                print(json.dumps({'id':name,'comparison':result['comparison'],'dispatch_ms':result['gpu']['dispatch_ms']}),flush=True)
            del x,rgb,alpha,valid,records
        b=plan['benchmark'];w,h=b['dimensions'];variant=b['variant']
        x,rgb,alpha,valid=lighting_gpu.fixture(w,h,plan['fixture_seed']+w+h)
        name='scene-1440p-benchmark';print('Starting '+name,flush=True)
        records=lighting_gpu.pack(diversity.select(x,variant),rgb,alpha,valid)
        result=run(out/name,a.exe,records,models[variant],binding['models'][variant],plan['limits'],b['warmup'],b['samples'])
        report['runs'].append({'id':name,'variant':variant,'kind':'benchmark','report_sha256':digest(out/name/'run.json'),**result})
        report['status']='succeeded'
    except Exception as error:report.update(status='failed',error=str(error));raise
    finally:save()
    print(json.dumps({'status':report['status'],'runs':len(report['runs']),'benchmark':result['gpu']}))


if __name__=='__main__':main()
