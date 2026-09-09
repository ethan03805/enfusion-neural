"""Blender: render the separately versioned point-light calibration fixture."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

import bpy

ROOT=Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path,data): path.write_bytes((json.dumps(data,indent=2,allow_nan=False)+'\n').encode('utf-8'))


def mesh_state(scene):
    values=[]
    for obj in sorted((o for o in scene.objects if o.type=='MESH'),key=lambda o:o.name):
        values.append({'name':obj.name,'matrix':[list(r) for r in obj.matrix_world],
            'vertices':[list(v.co) for v in obj.data.vertices],
            'faces':[[p.material_index,*p.vertices] for p in obj.data.polygons],
            'materials':[m.name for m in obj.data.materials], 'pass_index':obj.pass_index})
    return hashlib.sha256(json.dumps(values,sort_keys=True).encode('utf-8')).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',required=True);p.add_argument('--out',required=True)
    p.add_argument('--device',choices=['HIP','CPU'],default='CPU');p.add_argument('--device-name')
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    plan_path=ROOT/'scenes/point-light-calibration-v1.json';plan=read(plan_path);spec=plan['reference']
    base=Path(a.base).resolve();base_record=read(base/'run.json');base_evidence=read(ROOT/plan['base_evidence'])
    if (base_record['status']!='succeeded' or base_record['config_sha256']!=sha(ROOT/plan['source_scene'])
            or sha(base/'material-room.blend')!=base_evidence['source_artifacts']['blend_sha256']
            or base_record!=base_evidence['render_run']):
        raise ValueError('Original completed scene does not match published evidence')
    out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(__file__,out/'generator.py')
    write(out/'plan.json',plan)
    bpy.ops.wm.open_mainfile(filepath=str(base/'material-room.blend'))
    scene=bpy.context.scene;before=mesh_state(scene)
    if {o.name:o.pass_index for o in scene.objects if o.type=='MESH'}!=base_record['object_ids']:
        raise ValueError('Original object identities differ')
    lights=[o for o in scene.objects if o.type=='LIGHT']
    if len(lights)!=1 or lights[0].name!='ceiling-area' or lights[0].data.type!='AREA':
        raise ValueError('Expected the single original area light')
    bpy.data.objects.remove(lights[0],do_unlink=True)
    data=bpy.data.lights.new('calibration-point','POINT')
    data.energy=spec['power_watts'];data.color=(1,1,1);data.shadow_soft_size=spec['emitter_radius_m'];data.use_shadow=True
    if hasattr(data,'normalize'):data.normalize=True
    light=bpy.data.objects.new('calibration-point',data);scene.collection.objects.link(light)
    light.location=spec['position_blender_xyz']
    scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=spec['world_strength']
    scene.render.engine='CYCLES';scene.render.resolution_x,scene.render.resolution_y=plan['dimensions']
    scene.render.resolution_percentage=100;scene.render.dither_intensity=0
    scene.cycles.samples=spec['samples'];scene.cycles.use_denoising=False;scene.cycles.use_adaptive_sampling=False
    scene.cycles.sample_clamp_direct=0;scene.cycles.sample_clamp_indirect=0
    for key,value in spec['display'].items():setattr(scene.view_settings,key,value)
    scene.display_settings.display_device='sRGB'
    layer=scene.view_layers[0]
    layer.use_pass_z=layer.use_pass_normal=layer.use_pass_object_index=layer.use_pass_position=True
    devices=[]
    if a.device=='HIP':
        if not a.device_name:raise ValueError('HIP requires an exact device name')
        prefs=bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type='HIP';prefs.refresh_devices()
        for device in prefs.devices:
            device.use=device.type=='HIP' and device.name==a.device_name
            if device.use:devices.append({'type':device.type,'name':device.name})
        if len(devices)!=1:raise ValueError('Expected one selected HIP adapter')
        scene.cycles.device='GPU'
    else:
        scene.cycles.device='CPU';devices=[{'type':'CPU'}]
    bpy.context.view_layer.update()
    if mesh_state(scene)!=before:raise ValueError('Light replacement changed original mesh state')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'point-light.blend'))
    record={'schema_version':1,'status':'running','operation':'point-light-calibration-reference',
        'plan':plan,'plan_sha256':sha(plan_path),'generator_sha256':sha(__file__),
        'base_blend_sha256':sha(base/'material-room.blend'),'base_evidence_sha256':sha(ROOT/plan['base_evidence']),
        'base_record_sha256':sha(base/'run.json'),'base_config':base_record['config'],
        'object_ids':base_record['object_ids'],'mesh_state_sha256':before,
        'camera_matrix':[list(r) for r in scene.camera.matrix_world],
        'camera':{'sensor_fit':scene.camera.data.sensor_fit,'sensor_height':scene.camera.data.sensor_height,'lens':scene.camera.data.lens},
        'native_light':{'type':data.type,'energy':data.energy,'color':list(data.color),'position':list(light.location),
                        'emitter_radius':data.shadow_soft_size,'normalize':getattr(data,'normalize',None)},
        'color':spec['display'],'display_device':scene.display_settings.display_device,'dither_intensity':scene.render.dither_intensity,
        'blender':bpy.app.version_string,'devices':devices,'renders':[],
        'scope':'Offline original Cycles point-light fixture; no claim of Enfusion/reference appearance equivalence or live performance'}
    write(out/'run.json',record)
    try:
        for role in spec['roles']:
            bounces=spec['direct_max_bounces'] if role.startswith('direct') else spec['multibounce_max_bounces']
            scene.cycles.max_bounces=scene.cycles.diffuse_bounces=scene.cycles.glossy_bounces=bounces
            scene.cycles.seed=spec['seeds'][1 if role.endswith('_check') else 0]
            scene.render.image_settings.media_type='MULTI_LAYER_IMAGE'
            scene.render.image_settings.file_format='OPEN_EXR_MULTILAYER';scene.render.image_settings.color_depth='32'
            scene.render.image_settings.color_mode='RGBA';scene.render.filepath=str(out/(role+'.exr'))
            started=time.perf_counter();bpy.ops.render.render(write_still=True);seconds=time.perf_counter()-started
            scene.render.image_settings.media_type='IMAGE';scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_depth='8'
            bpy.data.images['Render Result'].save_render(str(out/(role+'.png')),scene=scene)
            entry={'role':role,'samples':scene.cycles.samples,'seed':scene.cycles.seed,'max_bounces':bounces,'seconds':seconds,
                'exr_sha256':sha(out/(role+'.exr')),'png_sha256':sha(out/(role+'.png'))}
            record['renders'].append(entry);write(out/'run.json',record)
            print('ENR_POINT_REFERENCE '+json.dumps(entry),flush=True)
        record['status']='succeeded'
    except Exception:
        record['status']='failed';raise
    finally:write(out/'run.json',record)


if __name__=='__main__':main()
