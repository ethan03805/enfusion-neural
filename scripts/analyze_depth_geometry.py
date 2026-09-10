"""Reserved checkerboard comparison with selected offline collision samples."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import shutil
import sys

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr.references import digest, write_json


def metrics(prediction, truth, aligned_inverse):
    positive = aligned_inverse > 0
    relative = np.full(len(truth), np.inf)
    relative[positive] = np.abs(1/aligned_inverse[positive]-truth[positive])/truth[positive]
    return {'count':len(truth),'spearman':float(spearmanr(prediction,1/truth).statistic),
        'median_relative_depth_error':float(np.median(relative)),
        'p95_relative_depth_error':float(np.percentile(relative,95)),
        'nonpositive_inverse_fraction':float(np.mean(~positive))}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--depth-run',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();run=a.depth_run.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(__file__,out/'driver.py')
    parent=json.loads((run/'report.json').read_text())
    if parent['status']!='completed' or not parent['parity_pass']:raise ValueError('Depth run not parity-passing')
    plan_path=ROOT/'scenes/playable-depth-evaluation-v1.json';plan=json.loads(plan_path.read_text())
    if digest(plan_path)!=parent['plan_sha256']:raise ValueError('Changed plan')
    geo_dir=ROOT/'runs/geometry-analysis-street-v2';geo_path=geo_dir/'report.json'
    geo=json.loads(geo_path.read_text());mode=geo['modes'][0]
    if not mode['reprojection_error_pixels']['passes']:raise ValueError('Projection control failed')
    data_path=geo_dir/'mode-0.npy'
    if digest(data_path)!=mode['arrays_sha256']:raise ValueError('Changed geometry')
    for path,sha in geo['source_hashes'].items():
        if digest(ROOT/path)!=sha:raise ValueError('Changed geometry source: '+path)
    data=np.load(data_path)
    raw_dir=ROOT/'runs/playable-geometry-probe-v1/runs'/geo['run']
    log=(raw_dir/'console.log').read_text()
    meta=re.findall(r'ENR_RAY_HIT mode=0 index=(\d+) mesh=(.*?) material=(.*?) collider=([^\r\n]*)',log)
    if [int(r[0]) for r in meta]!=list(range(2304)):raise ValueError('Invalid ray index sequence')
    i=next(i for i,r in enumerate(parent['images']) if r['name']=='street'); row=parent['images'][i]
    depth_path=run/f'{i:02d}-full-depth.npy'
    if digest(depth_path)!=row['full_depth_sha256'] or digest(raw_dir/'frame.png')!=row['source_sha256']:raise ValueError('Changed depth/source')
    depth=np.load(depth_path)
    if list(depth.shape)!=list(reversed(geo['dimensions'])):raise ValueError('Image dimensions differ')
    if not np.all(data[:,:2]==data[:,:2].astype(int)):raise ValueError('Expected integer pixel samples')
    forward=np.array(geo['direction']);forward/=np.linalg.norm(forward)
    axial=250*data[:,12]*(data[:,6:9]@forward)
    building=np.array(['/Houses/' in r[1] or '/Commercial/' in r[1] for r in meta])
    ground=np.array([not r[1].strip() for r in meta]) & (data[:,15]>.5)
    selected=(data[:,12]>0)&(data[:,12]<1)&(np.abs(np.linalg.norm(data[:,14:17],axis=1)-1)<=.01)&(building|ground)&(axial>=1)&(axial<=200)
    indices=np.flatnonzero(selected);truth=axial[selected]
    prediction=depth[data[selected,1].astype(int),data[selected,0].astype(int)].astype(np.float64)
    # x and y are coordinates in the declared 64x36 sample grid, not screen pixels.
    calibrate=((indices%64+indices//64)%2)==0
    matrix=np.column_stack([prediction,np.ones_like(prediction)])
    coef,_,rank,_=np.linalg.lstsq(matrix[calibrate],1/truth[calibrate],rcond=None)
    if rank!=2:raise ValueError('Rank deficient calibration')
    aligned=matrix@coef
    rows=[]
    for j,index in enumerate(indices):
        rows.append({'grid_index':int(index),'pixel':data[index,:2].astype(int).tolist(),
            'split':'calibration' if calibrate[j] else 'reserved','category':'building' if building[index] else 'ground',
            'mesh':meta[index][1],'axial_metres':float(truth[j]),'model_output':float(prediction[j]),'aligned_inverse_metres':float(aligned[j])})
    write_json(out/'samples.json',rows)
    result={name:metrics(prediction[mask],truth[mask],aligned[mask]) for name,mask in [('calibration',calibrate),('reserved',~calibrate)]}
    result['reserved_by_category']={name:metrics(prediction[mask],truth[mask],aligned[mask]) for name,mask in [('ground',(~calibrate)&ground[selected]),('building',(~calibrate)&building[selected])]}
    gates=plan['geometry_gates'];reserved=result['reserved']
    passed=reserved['spearman']>=gates['reserved_spearman_min'] and reserved['median_relative_depth_error']<=gates['reserved_median_relative_depth_error_max'] and reserved['nonpositive_inverse_fraction']<=gates['nonpositive_reserved_inverse_depth_max_fraction']
    report={'schema_version':1,'status':'completed','depth_run':run.relative_to(ROOT).as_posix(),
        'depth_report_sha256':digest(run/'report.json'),'geometry_report_sha256':digest(geo_path),
        'geometry_array_sha256':digest(data_path),'plan_sha256':digest(plan_path),'driver_sha256':digest(Path(__file__)),
        'samples_sha256':digest(out/'samples.json'),'selected_count':len(indices),'selected_categories':dict(Counter(r['category'] for r in rows)),
        'affine_inverse_depth_coefficients':coef.tolist(),'results':result,'declared_geometry_gate_pass':bool(passed),
        'scope':'One spatial checkerboard split in one fixed street view. Calibration uses grid indices x+y even. Unweighted least-squares fit on calibration cells only; reserved cells receive the same scale/offset. Collisions are not synchronized visible-surface ground truth. No claim for openings, foliage, metric generalization, normals or temporal stability.'}
    write_json(out/'report.json',report);print(json.dumps(report,indent=2))


if __name__=='__main__':main()
