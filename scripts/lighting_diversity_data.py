"""Load hash-verified source buffers and paired targets for the frozen plan."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr import lighting,temporal
from check_material_room import read_exr
from train_lighting_study import channels,metric

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,data):Path(path).write_bytes((json.dumps(data,indent=2,allow_nan=False)+'\n').encode('utf-8'))


def load_case(root,run,case):
    plan=run['plan'];scene=run['scenes'][case['scene_id']];folder=Path(root)/case['id']
    if sha(ROOT/'scenes'/scene['scene'])!=scene['config_sha256'] or sha(ROOT/'scenes'/scene['config']['material_library'])!=scene['material_library_sha256']:
        raise ValueError('Scene definition changed')
    expected={'source','reference'} if case['split']=='train' else {'source','reference','independent'}
    if len(case['renders'])!=len(expected) or {r['role'] for r in case['renders']}!=expected:raise ValueError('Missing or duplicate render roles')
    data={}
    for r in case['renders']:
        role=r['role'];samples=plan['evaluation_samples'] if case['split']=='test' else plan['samples']
        seed=plan['independent_seed' if role=='independent' else 'paired_seed']+case['index']*plan['seed_stride']
        bounces=plan['source_diffuse_bounces' if role=='source' else 'reference_diffuse_bounces']
        if r['samples']!=samples or r['seed']!=seed or r['diffuse_bounces']!=bounces:raise ValueError('Render controls changed')
        for ext in ('png','exr'):
            if sha(folder/(role+'.'+ext))!=r[ext+'_sha256']:raise ValueError('Raw render changed')
        data[role]=read_exr(folder/(role+'.exr'))
    source,reference=data['source'],data['reference']
    geometry={k:bool(np.array_equal(source[k],reference[k])) for k in ('ViewLayer.Depth.Z','ViewLayer.Object Index.X')}
    if not all(geometry.values()):raise ValueError('Source/reference geometry differs')
    ids=source['ViewLayer.Object Index.X'].astype(np.int32);valid=(ids>0)&(source['ViewLayer.Depth.Z']<100)
    rgb=channels(source,'Combined','RGB');target=channels(reference,'Combined','RGB')
    position=channels(source,'Position','XYZ');normal=channels(source,'Normal','XYZ')
    position[~valid]=0;normal[~valid]=0
    h,w=ids.shape
    if [w,h]!=plan['dimensions']:raise ValueError('Wrong dimensions')
    materials=np.zeros((max(o['id'] for o in scene['objects'].values())+1,5),np.float32)
    for obj in scene['objects'].values():
        mat=scene['config']['materials'][obj['material']]
        materials[obj['id']]=mat['base_color_linear']+[mat['roughness'],mat['metallic']]
    if ids.min()<0 or ids.max()>=len(materials):raise ValueError('Unrecognized object ID')
    x=lighting.features(rgb,position,normal,materials[ids],case['camera'],case['light'])
    xy,_=temporal.project(position,case['camera_matrix'],plan['vertical_fov_degrees'])
    yy,xx=np.indices(ids.shape);inside=temporal.interior(ids)
    geometry['self_projection_p95_pixels']=float(np.quantile(np.linalg.norm(xy-np.stack([xx,yy],-1),axis=-1)[inside],.95))
    if geometry['self_projection_p95_pixels']>1:raise ValueError('Camera/surface projection mismatch')
    return {'x':x,'y':np.log1p(target)-np.log1p(rgb),'rgb':rgb,'target':target,'position':position,'normal':normal,'ids':ids,
            'valid':valid,'alpha':source['ViewLayer.Combined.A'],'geometry':geometry,
            'independent':channels(data['independent'],'Combined','RGB') if 'independent' in data else None}
