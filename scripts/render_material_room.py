"""Run with Blender --background --factory-startup --python this.py -- --out NEW_DIR.

Original shared geometry, camera and material graph; limited-bounce source and
multi-bounce reference. No downloaded assets, denoising or generated imagery.
"""
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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",required=True)
    p.add_argument("--config",default=str(ROOT/"scenes/material-room-v1.json"))
    p.add_argument("--device",choices=["CPU","HIP"],default="CPU")
    p.add_argument("--device-name",help="Exact HIP device name; prevents selecting additional adapters")
    args = p.parse_args(sys.argv[sys.argv.index("--")+1:])
    out = Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=False)
    c = json.loads(Path(args.config).read_text())
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = False
    devices = []
    if args.device == "HIP":
        if not args.device_name: raise ValueError("HIP requires --device-name")
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "HIP"; prefs.refresh_devices()
        for device in prefs.devices:
            device.use = device.type == "HIP" and device.name == args.device_name
            if device.use: devices.append({"name":device.name,"type":device.type})
        if not devices: raise RuntimeError("No HIP device; choose CPU explicitly")
        scene.cycles.device = "GPU"
    else:
        scene.cycles.device = "CPU"; devices = [{"type":"CPU"}]
    scene.render.resolution_x,scene.render.resolution_y = c["dimensions"]
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.view_transform = c["color"]["view_transform"]
    scene.view_settings.look = c["color"]["look"]
    scene.view_settings.exposure = c["color"]["exposure"]
    scene.view_settings.gamma = c["color"]["gamma"]
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0
    materials = {}
    for name,definition in c["materials"].items():
        material = bpy.data.materials.new(name); material.use_nodes = True
        shader = material.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Base Color"].default_value = (*definition["base_color_linear"],1)
        shader.inputs["Roughness"].default_value = definition["roughness"]
        shader.inputs["Metallic"].default_value = definition["metallic"]
        materials[name] = material
    geometry = []
    def finish(obj,name,material):
        obj.name = name; obj.data.materials.append(materials[material]); geometry.append(obj)
    for box in c["boxes"]:
        bpy.ops.mesh.primitive_cube_add(size=1,location=box["position"])
        obj = bpy.context.object; obj.scale = box["size"]
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        finish(obj,box["id"],box["material"])
    for sphere in c["spheres"]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=96,ring_count=64,radius=sphere["radius"],location=sphere["position"])
        obj = bpy.context.object
        for face in obj.data.polygons: face.use_smooth = True
        finish(obj,sphere["id"],sphere["material"])
    posts = c["thin_posts"]
    for i,(x,diameter) in enumerate(zip(posts["x_positions"],posts["diameters_m"])):
        bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=diameter/2,depth=posts["height_m"],location=(x,posts["y"],posts["height_m"]/2))
        finish(bpy.context.object,f"post-{i}",posts["material"])
    data = bpy.data.lights.new("ceiling-area","AREA"); data.energy = c["light"]["power_watts"]; data.shape = "SQUARE"; data.size = c["light"]["size_m"]
    obj = bpy.data.objects.new("ceiling-area",data); scene.collection.objects.link(obj); obj.location = c["light"]["position"]
    data = bpy.data.cameras.new("reference-camera"); cam = bpy.data.objects.new("reference-camera",data); scene.collection.objects.link(cam)
    cam.location = c["camera"]["position"]; cam.rotation_euler = (Vector(c["camera"]["target"])-cam.location).to_track_quat("-Z","Y").to_euler()
    data.sensor_fit = "VERTICAL"; data.sensor_height = 24; data.lens = 12/math.tan(math.radians(c["camera"]["vertical_fov_degrees"])/2)
    data.clip_start = .01; data.clip_end = 100; scene.camera = cam
    layer = scene.view_layers[0]; layer.use_pass_z = True; layer.use_pass_normal = True; layer.use_pass_object_index = True
    for i,obj in enumerate(geometry,1): obj.pass_index = i
    bpy.ops.wm.save_as_mainfile(filepath=str(out/"material-room.blend"))
    bpy.ops.object.select_all(action="DESELECT")
    for obj in geometry: obj.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(out/"material-room.fbx"),use_selection=True,object_types={"MESH"},axis_forward="-Z",axis_up="Y",add_leaf_bones=False,bake_anim=False)
    record = {"schema_version":1,"status":"running","config":c,"config_sha256":sha(args.config),
              "generator_sha256":sha(__file__),"blender":bpy.app.version_string,"devices":devices,
              "object_ids":{obj.name:obj.pass_index for obj in geometry},
              "camera_matrix":[list(row) for row in cam.matrix_world],"renders":[]}
    def save_record(): (out/"run.json").write_text(json.dumps(record,indent=2)+"\n")
    save_record()
    try:
        for role in ("source","reference","convergence_check"):
            quality = c[role]
            scene.cycles.samples = quality["samples"]; scene.cycles.seed = quality["seed"]
            bounces = quality.get("max_bounces",c["reference"]["max_bounces"])
            scene.cycles.max_bounces = bounces; scene.cycles.diffuse_bounces = bounces; scene.cycles.glossy_bounces = bounces
            # Save scene-linear EXR first, then the display-transformed PNG.
            # Blender 5.1 writes the auxiliary passes in separate EXR parts.
            if hasattr(scene.render.image_settings,"media_type"):
                scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
            scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
            scene.render.image_settings.color_depth = "32"
            scene.render.filepath = str(out/(role+".exr"))
            started = time.monotonic(); bpy.ops.render.render(write_still=True)
            seconds = time.monotonic()-started
            if hasattr(scene.render.image_settings,"media_type"):
                scene.render.image_settings.media_type = "IMAGE"
            scene.render.image_settings.file_format = "PNG"; scene.render.image_settings.color_depth = "8"
            bpy.data.images["Render Result"].save_render(str(out/(role+".png")),scene=scene)
            record["renders"].append({"role":role,"samples":quality["samples"],"seed":quality["seed"],"max_bounces":bounces,"seconds":seconds,
                                      "png_sha256":sha(out/(role+".png")),"exr_sha256":sha(out/(role+".exr"))})
            save_record()
        record["status"] = "succeeded"
    except Exception:
        record["status"] = "failed"; raise
    finally: save_record()


if __name__ == "__main__": main()
