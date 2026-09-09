"""Blender: original scene transfer and continuous camera/light pairs, serially."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value): path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")


def create_scene(config,plan):
    bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;scene.render.engine="CYCLES"
    scene.cycles.use_denoising=False;scene.cycles.use_adaptive_sampling=False
    scene.cycles.samples=plan["samples"];scene.cycles.max_bounces=plan["max_bounces"]
    scene.cycles.glossy_bounces=plan["glossy_bounces"]
    scene.cycles.transmission_bounces=12;scene.cycles.transparent_max_bounces=8
    scene.cycles.volume_bounces=0;scene.cycles.sample_clamp_direct=0;scene.cycles.sample_clamp_indirect=10
    scene.render.resolution_x,scene.render.resolution_y=plan["dimensions"]
    scene.render.resolution_percentage=100;scene.render.film_transparent=False
    for key,value in config["color"].items():setattr(scene.view_settings,key,value)
    scene.world.use_nodes=True;scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value=0
    materials={}
    for name,definition in config["materials"].items():
        mat=bpy.data.materials.new(name);mat.use_nodes=True
        shader=mat.node_tree.nodes.get("Principled BSDF")
        for key,value in [("Base Color",(*definition["base_color_linear"],1)),("Roughness",definition["roughness"]),("Metallic",definition["metallic"])]:
            shader.inputs[key].default_value=value
        materials[name]=mat
    objects={}
    def finish(obj,name,material):
        obj.name=name;obj.data.materials.append(materials[material]);obj.pass_index=len(objects)+1
        objects[name]={"id":obj.pass_index,"material":material}
    for box in config["boxes"]:
        bpy.ops.mesh.primitive_cube_add(size=1,location=box["position"])
        obj=bpy.context.object;obj.scale=box["size"];bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        finish(obj,box["id"],box["material"])
    for sphere in config["spheres"]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=96,ring_count=64,radius=sphere["radius"],location=sphere["position"])
        obj=bpy.context.object
        for face in obj.data.polygons:face.use_smooth=True
        finish(obj,sphere["id"],sphere["material"])
    posts=config["thin_posts"]
    for i,(x,diameter) in enumerate(zip(posts["x_positions"],posts["diameters_m"])):
        bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=diameter/2,depth=posts["height_m"],location=(x,posts["y"],posts["height_m"]/2))
        finish(bpy.context.object,"post-"+str(i),posts["material"])
    data=bpy.data.lights.new("ceiling-area","AREA");data.energy=plan["light_power_watts"];data.shape="SQUARE";data.size=plan["light_size_m"]
    light=bpy.data.objects.new("ceiling-area",data);scene.collection.objects.link(light)
    data=bpy.data.cameras.new("reference-camera");camera=bpy.data.objects.new("reference-camera",data);scene.collection.objects.link(camera)
    data.sensor_fit="VERTICAL";data.sensor_height=24;data.lens=12/math.tan(math.radians(plan["vertical_fov_degrees"])/2)
    data.clip_start=.01;data.clip_end=100;scene.camera=camera
    layer=scene.view_layers[0]
    layer.use_pass_z=layer.use_pass_normal=layer.use_pass_object_index=layer.use_pass_position=True
    return scene,camera,light,objects


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--out",required=True)
    p.add_argument("--plan",default=str(ROOT/"scenes/lighting-motion-v1.json"))
    p.add_argument("--device",choices=["CPU","HIP"],default="CPU");p.add_argument("--device-name")
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:]);plan=json.loads(Path(a.plan).read_text())
    for model in plan["models"].values():
        if sha(ROOT/model["path"])!=model["sha256"]:raise ValueError("Frozen model changed")
    if plan["frames"]<2 or plan["samples"]<1:raise ValueError("Invalid sequence size")
    out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
    devices=[]
    if a.device=="HIP":
        if not a.device_name:raise ValueError("HIP needs an exact device name")
        prefs=bpy.context.preferences.addons["cycles"].preferences;prefs.compute_device_type="HIP";prefs.refresh_devices()
        for device in prefs.devices:
            device.use=device.type=="HIP" and device.name==a.device_name
            if device.use:devices.append({"name":device.name,"type":device.type})
        if len(devices)!=1:raise ValueError("Select exactly one HIP device")
    else:devices=[{"type":"CPU"}]
    record={"schema_version":1,"status":"running","plan":plan,"plan_sha256":sha(a.plan),"generator_sha256":sha(__file__),
            "blender":bpy.app.version_string,"devices":devices,"sequences":[],
            "timing_scope":"Serial offline render call including pass generation and EXR write, not game frame time"}
    def save():write(out/"run.json",record)
    save()
    try:
        for definition in plan["sequences"]:
            path=ROOT/"scenes"/definition["scene"];config=json.loads(path.read_text());library_hash=None
            if "material_library" in config:
                library_path=ROOT/"scenes"/config["material_library"];library=json.loads(library_path.read_text())
                config["materials"]=library["materials"];config["color"]=library["color"];library_hash=sha(library_path)
            folder=out/definition["id"];folder.mkdir()
            scene,camera,light,objects=create_scene(config,plan)
            scene.cycles.device="GPU" if a.device=="HIP" else "CPU"
            entry={**definition,"config":config,"config_sha256":sha(path),"material_library_sha256":library_hash,
                   "objects":objects,"frames":[],"transport_settings":{k:getattr(scene.cycles,k) for k in
                     ["max_bounces","glossy_bounces","transmission_bounces","transparent_max_bounces","volume_bounces","sample_clamp_direct","sample_clamp_indirect"]}}
            record["sequences"].append(entry);save()
            for index in range(plan["frames"]):
                t=index/(plan["frames"]-1);u=t*t*(3-2*t)
                camera.location=Vector(plan["camera_start"]).lerp(Vector(plan["camera_end"]),u)
                camera.rotation_euler=(Vector(plan["camera_target"])-camera.location).to_track_quat("-Z","Y").to_euler()
                light.location=Vector(plan["light_start"]).lerp(Vector(plan["light_end"]),u)
                bpy.context.view_layer.update()
                if index==0:bpy.ops.wm.save_as_mainfile(filepath=str(folder/"scene.blend"));entry["blend_sha256"]=sha(folder/"scene.blend")
                frame={"index":index,"time_seconds":index/plan["playback_fps"],"camera":list(camera.location),"light":list(light.location),
                       "camera_matrix":[list(row) for row in camera.matrix_world],"renders":[]}
                entry["frames"].append(frame);frame_folder=folder/f"{index:04d}";frame_folder.mkdir();save()
                roles=["source","reference"] if index%2==0 else ["reference","source"]
                roles.append("independent")
                for role in roles:
                    scene.cycles.diffuse_bounces=plan["source_diffuse_bounces"] if role=="source" else plan["reference_diffuse_bounces"]
                    scene.cycles.seed=plan["independent_seed" if role=="independent" else "paired_seed"]+index*plan["seed_stride"]
                    settings=scene.render.image_settings;settings.media_type="MULTI_LAYER_IMAGE";settings.file_format="OPEN_EXR_MULTILAYER"
                    settings.color_mode="RGBA";settings.color_depth="32";scene.render.filepath=str(frame_folder/(role+".exr"))
                    started=time.perf_counter();bpy.ops.render.render(write_still=True);elapsed=time.perf_counter()-started
                    settings.media_type="IMAGE";settings.file_format="PNG";settings.color_depth="8"
                    bpy.data.images["Render Result"].save_render(str(frame_folder/(role+".png")),scene=scene)
                    frame["renders"].append({"role":role,"samples":scene.cycles.samples,"seed":scene.cycles.seed,
                        "diffuse_bounces":scene.cycles.diffuse_bounces,"seconds":elapsed,"png_sha256":sha(frame_folder/(role+".png")),"exr_sha256":sha(frame_folder/(role+".exr"))})
                    save();print("ENR_MOTION "+json.dumps({"sequence":definition["id"],"index":index,"role":role,"seconds":elapsed}),flush=True)
        record["status"]="succeeded"
    except Exception:record["status"]="failed";raise
    finally:save()


if __name__=="__main__":main()
