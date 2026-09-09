"""Blender: apply the same recorded display transform to all linear predictions.

The trainer writes top-down linear RGBA .npy files. Blender pixel arrays are
bottom-up. Validate the resulting reference PNG against the original render
before publishing any display image (see summarize_lighting_study.py).
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",required=True); p.add_argument("--renders",required=True)
    a = p.parse_args(sys.argv[sys.argv.index("--")+1:])
    root,renders = Path(a.root),Path(a.renders)
    run = json.loads((root/"run.json").read_text()); render = json.loads((renders/"run.json").read_text())
    if run["status"] != "succeeded" or run["renderer_run_sha256"] != hashlib.sha256((renders/"run.json").read_bytes()).hexdigest():
        raise ValueError("Incomplete training or mismatched render run")
    scene = bpy.context.scene; color = render["base_config"]["color"]
    for key,value in color.items(): setattr(scene.view_settings,key,value)
    scene.render.image_settings.file_format = "PNG"; scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    for case in run["cases"]:
        for name,record in case["outputs"].items():
            path = root/case["id"]/(name+".npy")
            if hashlib.sha256(path.read_bytes()).hexdigest() != record["linear_rgba_sha256"]: raise ValueError("Changed inference array")
            rgba = np.load(path,allow_pickle=False)
            h,w,c = rgba.shape
            if c != 4 or [w,h] != render["plan"]["dimensions"] or not np.isfinite(rgba).all(): raise ValueError("Invalid display input")
            image = bpy.data.images.new("lighting-display",width=w,height=h,alpha=True,float_buffer=True)
            image.colorspace_settings.name = "Linear Rec.709"
            image.pixels.foreach_set(np.ascontiguousarray(rgba[::-1]).reshape(-1))
            destination = root/case["id"]/(name+".png")
            if destination.exists(): raise ValueError("Display output exists")
            image.save_render(str(destination.resolve()),scene=scene)
            bpy.data.images.remove(image)
    (root/"display.json").write_text(json.dumps({"blender":bpy.app.version_string,"color":color,
        "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "operation":"Scene-linear RGBA to 8-bit PNG using identical AgX settings; flip rows for Blender storage; no retouching"},indent=2)+"\n")


if __name__ == "__main__": main()
