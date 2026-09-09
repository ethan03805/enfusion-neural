"""Freeze a candidate response curve using only declared fit images and the first reference pass."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr import photometry
from enr.references import digest
from check_material_room import read_exr


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',required=True);p.add_argument('--native-verified',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();out=Path(a.out)
    if out.exists():raise ValueError('Calibration lock already exists')
    plan_path=ROOT/'scenes/point-light-calibration-v1.json'
    plan=json.loads(plan_path.read_text(encoding='utf-8'));reference=Path(a.reference)
    record=json.loads((reference/'run.json').read_text(encoding='utf-8'))
    first=record['renders'][0]
    if (record['plan']!=plan or record['plan_sha256']!=digest(plan_path)
            or first['role']!='direct' or first['samples']!=plan['reference']['samples']
            or first['seed']!=plan['reference']['seeds'][0] or first['max_bounces']!=plan['reference']['direct_max_bounces']
            or first['exr_sha256']!=digest(reference/'direct.exr')):
        raise ValueError('Completed first reference pass differs')
    native=json.loads(Path(a.native_verified).read_text(encoding='utf-8'))
    if native['status']!='succeeded':raise ValueError('Native verification incomplete')
    data=read_exr(reference/'direct.exr')
    linear=np.stack([data['ViewLayer.Combined.'+c] for c in 'RGB'],axis=-1)
    inputs=[];images={}
    for case in plan['fit_cases']:
        control=next(c for c in native['controls'] if c['light_case']==case)
        if control['light_control']['plan_sha256']!=digest(plan_path):raise ValueError('Native fit plan differs')
        path=ROOT/'experiments/local'/control['trial']/'runs'/control['run_id']/control['image']['file']
        if digest(path)!=control['image']['sha256']:raise ValueError('Fit image changed')
        images[case]=np.asarray(Image.open(path).convert('RGB'),dtype=np.float64)
        inputs.append({'case':case,'run_id':control['run_id'],'image_sha256':control['image']['sha256']})
    fit=photometry.fit_response(linear,images,plan)
    result={'schema_version':1,'operation':'point-light-calibration-lock','plan_sha256':digest(plan_path),
        'reference_exr_sha256':first['exr_sha256'],'reference_generator_sha256':record['generator_sha256'],
        'photometry_sha256':digest(ROOT/'enr/photometry.py'),'locker_sha256':digest(__file__),
        'native_fit_inputs':inputs,'fit':fit,
        'scope':'Fit uses only the first LV8/LV10/LV12 images and one declared back-wall patch. All other images/patches are excluded from fitting. The reference role named direct permits one bounce; it is not a direct-light-only renderer.'}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes((json.dumps(result,indent=2,allow_nan=False)+'\n').encode('utf-8'))
    print(json.dumps(fit))


if __name__=='__main__':main()
