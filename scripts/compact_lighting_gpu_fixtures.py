"""Reclaim reproducible numerical inputs only after byte-exact regeneration.

This never removes GPU outputs, measured run manifests, rendered inputs or failures.
The recipe and executed source snapshots are retained before removing redundant input.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import re

import numpy as np

from lighting_gpu_run import ROOT,write
from enr import lighting_gpu,diversity
from enr.references import digest


def compact(root, only=None):
    root=Path(root).resolve()
    permitted=(ROOT/'experiments/local').resolve()
    if not root.is_relative_to(permitted) or root==permitted or root.is_symlink():
        raise ValueError('Only a dedicated local numerical fixture run is eligible')
    batch=json.loads((root/'run.json').read_text(encoding='utf-8'))
    if batch['plan']['id']!='lighting-gpu-v1' or batch['gpu_contract_sha256']!=digest(ROOT/'enr/lighting_gpu.py'):
        raise ValueError('Fixture generator changed')
    if only is not None and not re.fullmatch(r'[a-z0-9-]+',only):raise ValueError('Invalid selected trial')
    retention=root/('fixture-retention'+('-'+only if only else ''))
    if retention.exists():raise ValueError('Fixture retention already recorded')
    retention.mkdir()
    for name in ['enr/lighting_gpu.py','enr/lighting.py','enr/diversity.py','scripts/compact_lighting_gpu_fixtures.py']:
        shutil.copyfile(ROOT/name,retention/Path(name).name)
    summary={'schema_version':1,'batch_sha256':digest(root/'run.json'),'numpy':np.__version__,'python':sys.version,
             'scope':'Generated random fixture inputs only; byte-exact regeneration verified before removal; all actual GPU outputs and failed input files retained',
             'snapshots':{p.name:digest(p) for p in retention.iterdir()},'files':[]}
    manifest=retention/'run.json';write(manifest,summary)
    cache=None;data=None
    for trial in batch['runs']:
        if only is not None and trial['id']!=only:continue
        if trial['status']!='succeeded' or trial['kind'] not in ('smoke','benchmark'):continue
        folder=(root/trial['id']).resolve()
        if folder.parent!=root or folder.is_symlink():raise ValueError('Unexpected fixture trial path')
        if digest(folder/'run.json')!=trial['report_sha256']:raise ValueError('Trial manifest changed')
        path=folder/'input.fp32'
        if path.is_symlink() or digest(path)!=trial['input_sha256']:raise ValueError('Input changed')
        w,h=trial['dimensions']
        seed=batch['plan']['fixture_seed']+w+h
        if cache!=(w,h,seed):
            data=lighting_gpu.fixture(w,h,seed);cache=(w,h,seed)
        x,rgb,alpha,valid=data
        records=lighting_gpu.pack(diversity.select(x,trial['variant']),rgb,alpha,valid)
        regenerated=hashlib.sha256(memoryview(records)).hexdigest()
        if regenerated!=trial['input_sha256'] or path.stat().st_size!=records.nbytes:
            raise ValueError('Fixture regeneration differs')
        entry={'file':path.relative_to(root).as_posix(),'sha256':regenerated,'bytes':records.nbytes,
               'dimensions':[w,h],'seed':seed,'variant':trial['variant'],'byte_exact_regeneration':True,'removed':False}
        summary['files'].append(entry);write(manifest,summary)
        # The resolved file is inside this experiment, generated here, and exactly reproducible above.
        path.unlink();entry['removed']=True;write(manifest,summary)
        print('Reclaimed '+entry['file'],flush=True)
    if not summary['files']:raise ValueError('No eligible completed numerical fixture')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--only');a=p.parse_args()
    r=compact(a.root,a.only);print(json.dumps({'files':len(r['files']),'logical_bytes_removed':sum(v['bytes'] for v in r['files'])}))
