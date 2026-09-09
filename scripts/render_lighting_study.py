"""Render matched diffuse-bounce pairs from the original material-room .blend.

Run in Blender; first generate the base with render_material_room.py. All other
sampling/transport settings remain fixed. GPU jobs execute serially.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path, value): path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", required=True, help="Completed material-room generator directory")
    p.add_argument("--out", required=True)
    p.add_argument("--plan", default=str(ROOT/"scenes/lighting-study-v1.json"))
    p.add_argument("--device", choices=["CPU", "HIP"], default="CPU")
    p.add_argument("--device-name")
    a = p.parse_args(sys.argv[sys.argv.index("--")+1:])
    plan = json.loads(Path(a.plan).read_text())
    base = Path(a.base).resolve()
    base_record = json.loads((base/"run.json").read_text())
    if base_record["status"] != "succeeded": raise ValueError("Incomplete base scene")
    if base_record["config_sha256"] != sha(ROOT/"scenes/material-room-v1.json"):
        raise ValueError("Base scene configuration does not match the versioned scene")
    ids = [case["id"] for case in plan["cases"]]
    if len(set(ids)) != len(ids) or any(not name.replace("-", "").isalnum() for name in ids):
        raise ValueError("Invalid case IDs")
    if plan["source_diffuse_bounces"] >= plan["reference_diffuse_bounces"]:
        raise ValueError("Source must use fewer diffuse bounces")
    out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.open_mainfile(filepath=str(base/"material-room.blend"))
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.samples = plan["samples"]
    scene.cycles.max_bounces = plan["max_bounces"]
    scene.cycles.glossy_bounces = plan["glossy_bounces"]
    scene.render.resolution_x, scene.render.resolution_y = plan["dimensions"]
    scene.render.resolution_percentage = 100
    layer = scene.view_layers[0]
    layer.use_pass_z = layer.use_pass_normal = layer.use_pass_object_index = True
    layer.use_pass_position = True
    devices = []
    if a.device == "HIP":
        if not a.device_name: raise ValueError("HIP requires an exact device name")
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "HIP"; prefs.refresh_devices()
        for device in prefs.devices:
            device.use = device.type == "HIP" and device.name == a.device_name
            if device.use: devices.append({"name":device.name,"type":device.type})
        if len(devices) != 1: raise ValueError("Expected exactly one selected HIP adapter")
        scene.cycles.device = "GPU"
    else:
        scene.cycles.device = "CPU"; devices = [{"type":"CPU"}]
    light = bpy.data.objects["ceiling-area"]
    light.data.energy = plan["light_power_watts"]; light.data.size = plan["light_size_m"]
    record = {"schema_version":1,"status":"running","plan":plan,"plan_sha256":sha(a.plan),
              "base_blend_sha256":sha(base/"material-room.blend"),"base_config":base_record["config"],
              "base_record_sha256":sha(base/"run.json"),"generator_sha256":sha(__file__),
              "blender":bpy.app.version_string,"devices":devices,"cases":[],
              "transport_settings":{key:getattr(scene.cycles,key) for key in
                  ["max_bounces","glossy_bounces","transmission_bounces","transparent_max_bounces","volume_bounces","sample_clamp_direct","sample_clamp_indirect"]},
              "object_ids":base_record["object_ids"],
              "timing_scope":"Offline Blender render call including pass generation and EXR write; not engine or real-time GPU dispatch"}
    def save(): write(out/"run.json",record)
    save()
    try:
        for index, case in enumerate(plan["cases"]):
            folder = out/case["id"]; folder.mkdir()
            scene.camera.location = case["camera"]
            scene.camera.rotation_euler = (Vector(plan["camera_target"])-scene.camera.location).to_track_quat("-Z","Y").to_euler()
            light.location = case["light"]
            bpy.context.view_layer.update()
            entry = {**case,"camera_matrix":[list(row) for row in scene.camera.matrix_world],"renders":[]}
            record["cases"].append(entry); save()
            # Alternate order to make systematic first-render overhead visible.
            roles = ["source","reference"] if index % 2 == 0 else ["reference","source"]
            if case["id"] in plan["noise_check_cases"]: roles.append("noise_check")
            for role in roles:
                scene.cycles.diffuse_bounces = plan["source_diffuse_bounces"] if role == "source" else plan["reference_diffuse_bounces"]
                scene.cycles.seed = plan["noise_check_seed"] if role == "noise_check" else plan["seed"]
                scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
                scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
                scene.render.image_settings.color_mode = "RGBA"; scene.render.image_settings.color_depth = "32"
                scene.render.filepath = str(folder/(role+".exr"))
                start = time.perf_counter(); bpy.ops.render.render(write_still=True)
                elapsed = time.perf_counter()-start
                scene.render.image_settings.media_type = "IMAGE"
                scene.render.image_settings.file_format = "PNG"; scene.render.image_settings.color_depth = "8"
                bpy.data.images["Render Result"].save_render(str(folder/(role+".png")), scene=scene)
                entry["renders"].append({"role":role,"samples":scene.cycles.samples,"seed":scene.cycles.seed,
                                         "diffuse_bounces":scene.cycles.diffuse_bounces,"seconds":elapsed,
                                         "png_sha256":sha(folder/(role+".png")),"exr_sha256":sha(folder/(role+".exr"))})
                save()
                print("ENR_LIGHTING "+json.dumps({"case":case["id"],"role":role,"seconds":elapsed}),flush=True)
        record["status"] = "succeeded"
    except Exception:
        record["status"] = "failed"; raise
    finally: save()


if __name__ == "__main__": main()
