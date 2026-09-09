"""Blender: render preregistered disjoint lighting layouts, serially.

The test phase requires a model lock produced without test access.
"""
import argparse
import json
from pathlib import Path
import sys
import time

import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from render_lighting_motion import create_scene,sha,write


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',required=True);p.add_argument('--phase',choices=['fit','test'],required=True)
    p.add_argument('--plan',default=str(ROOT/'scenes/lighting-diversity-v1.json'))
    p.add_argument('--model-lock');p.add_argument('--device',choices=['CPU','HIP'],default='CPU');p.add_argument('--device-name')
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);plan=json.loads(Path(a.plan).read_text())
    lock=None
    if a.phase=='test':
        if not a.model_lock:raise ValueError('Test access requires a completed model lock')
        lock_path=Path(a.model_lock).resolve();lock=json.loads(lock_path.read_text())
        if lock['plan_sha256']!=sha(a.plan) or not lock['training_complete'] or lock['test_accessed']:
            raise ValueError('Invalid preregistered model lock')
        for entry in lock['models'].values():
            if sha(lock_path.parent/entry['file'])!=entry['sha256']:raise ValueError('Locked model changed')
    out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
    devices=[]
    if a.device=='HIP':
        if not a.device_name:raise ValueError('HIP requires one exact device name')
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='HIP';prefs.refresh_devices()
        for d in prefs.devices:
            d.use=d.type=='HIP' and d.name==a.device_name
            if d.use:devices.append({'name':d.name,'type':d.type})
        if len(devices)!=1:raise ValueError('Select exactly one HIP device')
    else:devices=[{'type':'CPU'}]
    record={'schema_version':1,'status':'running','phase':a.phase,'plan':plan,'plan_sha256':sha(a.plan),
            'generator_sha256':sha(__file__),'scene_builder_sha256':sha(ROOT/'scripts/render_lighting_motion.py'),
            'blender':bpy.app.version_string,'devices':devices,'scenes':{},'cases':[],
            'model_lock_sha256':sha(a.model_lock) if lock else None,'model_lock':lock,
            'timing_scope':'Offline serial render calls including passes and EXR I/O; not engine frame cost'}
    def save():write(out/'run.json',record)
    save()
    try:
        for definition in plan['scenes']:
            if (definition['split']=='test') != (a.phase=='test'):continue
            path=ROOT/'scenes'/definition['scene'];cfg=json.loads(path.read_text())
            lib_path=ROOT/'scenes'/cfg['material_library'];lib=json.loads(lib_path.read_text())
            cfg['materials']=lib['materials'];cfg['color']=lib['color']
            record['base_config']={'color':cfg['color']}
            scene,camera,light,objects=create_scene(cfg,plan)
            scene.cycles.device='GPU' if a.device=='HIP' else 'CPU'
            scene.cycles.samples=plan['evaluation_samples'] if a.phase=='test' else plan['samples']
            scene_record={**definition,'config':cfg,'config_sha256':sha(path),'material_library_sha256':sha(lib_path),'objects':objects,
                          'transport_settings':{k:getattr(scene.cycles,k) for k in ['max_bounces','glossy_bounces','transmission_bounces','transparent_max_bounces','volume_bounces','sample_clamp_direct','sample_clamp_indirect']}}
            record['scenes'][definition['id']]=scene_record
            if a.phase=='fit':cases=[c for c in plan['cases'] if c['scene_id']==definition['id']]
            else:
                motion=plan['test_sequence'];cases=[]
                for i in range(motion['frames']):
                    t=i/(motion['frames']-1);u=t*t*(3-2*t)
                    cases.append({'id':definition['id']+'-'+str(i).zfill(4),'index':i,'split':'test','scene_id':definition['id'],'group':definition['group'],
                                  'camera':list(Vector(motion['camera_start']).lerp(Vector(motion['camera_end']),u)),
                                  'light':list(Vector(motion['light_start']).lerp(Vector(motion['light_end']),u)),
                                  'time_seconds':i/motion['playback_fps']})
            for c in cases:
                camera.location=Vector(c['camera']);camera.rotation_euler=(Vector(plan['camera_target'])-camera.location).to_track_quat('-Z','Y').to_euler()
                light.location=Vector(c['light']);bpy.context.view_layer.update()
                if c['index']==0:
                    blend=out/(definition['id']+'.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend));scene_record['blend_sha256']=sha(blend)
                folder=out/c['id'];folder.mkdir()
                entry={**c,'camera_matrix':[list(row) for row in camera.matrix_world],'renders':[]};record['cases'].append(entry);save()
                roles=['source','reference'] if c['index']%2==0 else ['reference','source']
                if c['split']!='train':roles.append('independent')
                for role in roles:
                    scene.cycles.diffuse_bounces=plan['source_diffuse_bounces'] if role=='source' else plan['reference_diffuse_bounces']
                    scene.cycles.seed=plan['independent_seed' if role=='independent' else 'paired_seed']+c['index']*plan['seed_stride']
                    settings=scene.render.image_settings;settings.media_type='MULTI_LAYER_IMAGE';settings.file_format='OPEN_EXR_MULTILAYER'
                    settings.color_mode='RGBA';settings.color_depth='32';scene.render.filepath=str(folder/(role+'.exr'))
                    start=time.perf_counter();bpy.ops.render.render(write_still=True);elapsed=time.perf_counter()-start
                    settings.media_type='IMAGE';settings.file_format='PNG';settings.color_depth='8'
                    bpy.data.images['Render Result'].save_render(str(folder/(role+'.png')),scene=scene)
                    entry['renders'].append({'role':role,'samples':scene.cycles.samples,'seed':scene.cycles.seed,'diffuse_bounces':scene.cycles.diffuse_bounces,
                                             'seconds':elapsed,'png_sha256':sha(folder/(role+'.png')),'exr_sha256':sha(folder/(role+'.exr'))})
                    save();print('ENR_DIVERSITY '+json.dumps({'case':c['id'],'role':role,'seconds':elapsed}),flush=True)
        record['status']='succeeded'
    except Exception:record['status']='failed';raise
    finally:save()


if __name__=='__main__':main()
