"""Sample an Enfusion camera path through an isolated Enfusion Lab project."""
import argparse
from contextlib import contextmanager
from datetime import date
import json
import math
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

from .references import ROOT, digest, lab_modules, number, scene_config, write_json


def load_config(path, *, validated_world=None):
    """Keep the Arland default; bridge callers can supply a natively observed world."""
    c = json.loads(Path(path).read_text(encoding="utf-8"))
    if c["schema_version"] != 1 or c["split"] != "diagnostic":
        raise ValueError("Sequence data is diagnostic only")
    for key in ("position_start", "position_end"):
        if len(c[key]) != 3: raise ValueError("Camera needs three coordinates")
        for x in c[key]: number(x, -1e6, 1e6, key)
    for key, low, high in [("yaw_start_degrees",-360,360),("yaw_end_degrees",-360,360),
                          ("vertical_fov_degrees",10,120),("hdr_brightness",1e-6,100),
                          ("near_plane_m",.001,10),("far_plane_m",10,20000),
                          ("hour",0,24),("wind_speed_mps",0,100),("wind_direction_degrees",0,360),
                          ("settle_seconds",1,60),("timeout_seconds",10,600),
                          ("samples",1,300),("hold_ticks_per_sample",3,120),("playback_fps",1,60)]:
        number(c[key], low, high, key)
    if len(c["date"]) != 3 or any(type(v) is not int for v in c["date"]):
        raise ValueError("Date must contain three integers")
    date(*c["date"])
    if c["near_plane_m"] >= c["far_plane_m"] or c["timeout_seconds"] <= c["settle_seconds"]:
        raise ValueError("Invalid clip planes or capture timeout")
    for key in ("samples", "hold_ticks_per_sample", "playback_fps"):
        if type(c[key]) is not int: raise ValueError(key + " must be an integer")
    if len(c["dimensions"]) != 2 or any(type(v) is not int or v < 128 or v > 7680 for v in c["dimensions"]):
        raise ValueError("Invalid dimensions")
    if (c["world"] != "worlds/Arland/Arland.ent" and (validated_world is None or c["world"] != validated_world)) or c["weather_state"] != "Clear":
        raise ValueError("This adapter currently supports the documented Arland path")
    if c["quality_file"] != "adapters/enfusion/sequence/ENR_Engine.conf":
        raise ValueError("Unknown quality preset")
    return c


def camera(c, index):
    t = index / (c["samples"] - 1) if c["samples"] > 1 else 0
    p = np.array(c["position_start"]) + t * (np.array(c["position_end"]) - c["position_start"])
    yaw = math.radians(c["yaw_start_degrees"] + t*(c["yaw_end_degrees"]-c["yaw_start_degrees"]))
    return p.tolist(), [math.sin(yaw), 0, math.cos(yaw)]


def prepare(project, c):
    project = Path(project)
    source = ROOT / "adapters/enfusion/sequence"
    for name in ("ELab_GameCapture.c", "ENR_Sequence.c", "ENR_Settings.c"):
        shutil.copyfile(source/name, project/"addon/Scripts/Game"/name)
    shutil.copyfile(source/"ELab_CapturePlugin.c", project/"addon/Scripts/WorkbenchGame/ELab_CapturePlugin.c")
    shutil.copyfile(ROOT/c["quality_file"], project/"addon/ENR_Engine.conf")
    # New files on every run; Workbench's registry and saved diagnostic overrides are isolated.
    (project/"addon/ENR_Workbench.ini").write_text("", encoding="utf-8")
    (project/"addon/ENR_Diag.txt").write_text("", encoding="utf-8")
    env = scene_config({"defaults":c}, {"hour":c["hour"]})
    (project/"addon/Scripts/Game/ENR_ReferenceConfig.c").write_text(env, encoding="utf-8")
    def vec(x): return '"'+' '.join(map(str,x))+'"'
    config = f'''#ifdef WORKBENCH
class ENR_SequenceConfig
{{
 static int Samples = {c['samples']};
 static int HoldTicks = {c['hold_ticks_per_sample']};
 static vector Start = {vec(c['position_start'])};
 static vector End = {vec(c['position_end'])};
 static float YawStart = {c['yaw_start_degrees']};
 static float YawEnd = {c['yaw_end_degrees']};
 static float FOV = {c['vertical_fov_degrees']};
 static float Near = {c['near_plane_m']};
 static float Far = {c['far_plane_m']};
 static float Exposure = {c['hdr_brightness']};
}}
#endif
'''
    (project/"addon/Scripts/Game/ENR_SequenceConfig.c").write_text(config, encoding="utf-8")


@contextmanager
def private_settings(runner):
    """Compatibility extension for Lab 0.1: CLI-local and not thread safe.

    The original runner still owns the process, lock, snapshot, timeout and sentinel
    validation. Restore its argument builder even after failure. Do not use this
    context from a server or concurrently with another Workbench operation.
    """
    original = runner.command_arguments
    def arguments(executable, game, directory, command, *args, **kwargs):
        result = original(executable, game, directory, command, *args, **kwargs)
        extras = ["-cfg",str(directory/"addon/ENR_Engine.conf"),
                  "-forceSettings",str(directory/"addon/ENR_Workbench.ini"),
                  "-diagMenu",str(directory/"addon/ENR_Diag.txt")]
        return result[:1] + extras + result[1:]
    runner.command_arguments = arguments
    try: yield
    finally: runner.command_arguments = original


def events(path):
    result = []
    for line in Path(path).read_text(encoding="utf-8",errors="replace").splitlines():
        if "ENR {" in line: result.append(json.loads(line[line.index("ENR {")+4:]))
    return result


def verify(c, run):
    if run.get("status") != "succeeded":
        raise ValueError("Workbench capture did not succeed")
    directory = Path(run["directory"])
    telemetry = events(directory/"console.log")
    actual_settings = {(e["module"],e["key"]):e["value"] for e in telemetry if e["event"] == "setting"}
    for module,fields in c["quality_readback"].items():
        for key,value in fields.items():
            if actual_settings.get((module,key)) != value:
                raise ValueError("Engine settings readback mismatch: "+module+"."+key)
    environment = [e for e in telemetry if e["event"] == "environment"]
    if len(environment) != 1 or environment[0]["date"] != c["date"] or environment[0]["weather_state"] != c["weather_state"]:
        raise ValueError("Environment mismatch")
    for key,target in [("hour",c["hour"]),("wind_speed_mps",c["wind_speed_mps"]),("wind_direction_degrees",c["wind_direction_degrees"])]:
        if not math.isclose(environment[0][key],target,abs_tol=.01): raise ValueError("Environment drift")
    samples = [e for e in telemetry if e["event"] == "sample"]
    projection = [e for e in telemetry if e["event"] == "projection"]
    if [e["index"] for e in samples] != list(range(c["samples"])) or [e["index"] for e in projection] != list(range(c["samples"])):
        raise ValueError("Missing, duplicated or reordered sample telemetry")
    files = sorted((directory/"profile/profile").glob("sample-*.png"))
    if [p.name for p in files] != [f"sample-{i:05d}.png" for i in range(c["samples"])]:
        raise ValueError("Unexpected frame files")
    w,h = c["dimensions"]
    delta = h/(20*math.tan(math.radians(c["vertical_fov_degrees"])/2))
    frames = []
    previous_time, previous_frame = -1,-1
    for i,(sample,proj,path) in enumerate(zip(samples,projection,files)):
        position,direction = camera(c,i)
        for key,target in [("position",position),("direction",direction)]:
            if not np.allclose(sample[key],target,atol=.01,rtol=0): raise ValueError("Camera mismatch")
        if type(sample["world_frame"]) is not int or not math.isfinite(sample["simulation_seconds"]):
            raise ValueError("Invalid capture time")
        if sample["world_frame"] <= previous_frame or sample["simulation_seconds"] <= previous_time:
            raise ValueError("Capture time did not advance")
        previous_time,previous_frame = sample["simulation_seconds"],sample["world_frame"]
        if sample["simulation_seconds"] < c["settle_seconds"]: raise ValueError("Insufficient settle")
        if [proj["width"],proj["height"]] != [w,h]: raise ValueError("Viewport size mismatch")
        for key,target in [("up_xy",[w/2,h/2-delta]),("right_xy",[w/2+delta,h/2])]:
            if not np.allclose(proj[key],target,atol=.03,rtol=0): raise ValueError("Projection mismatch")
        if not math.isclose(proj["hdr_brightness"],c["hdr_brightness"],rel_tol=1e-5): raise ValueError("Exposure mismatch")
        if not math.isclose(proj["far_plane"],c["far_plane_m"],rel_tol=1e-5): raise ValueError("Far plane mismatch")
        with Image.open(path) as image:
            if image.size != (w,h) or image.format != "PNG": raise ValueError("Image size/format mismatch")
            image.verify()
        frames.append({"index":i,"file":str(path.relative_to(directory)),"sha256":digest(path),
                       "camera":sample,"projection":proj})
    return {"schema_version":1,"status":"succeeded","run_id":run["run_id"],
            "scope":c["time_convention"],"dimensions":c["dimensions"],"playback_fps":c["playback_fps"],
            "config":c,"addon_sha256":run["addon_sha256"],"frames":frames,
            "settings_readback":[e for e in telemetry if e["event"] == "setting"],
            "environment":[e for e in telemetry if e["event"] == "environment"],
            "limits":["No proof of viewport internal resolution or FSR state; engine settings readback is a separate workspace.",
                      "Camera is held for several simulation ticks before each screenshot request; GPU presentation frame ID is unavailable.",
                      "No motion vectors, depth, HDR radiance or deterministic foliage phase."]}


def capture(config_path, root, source, static=False, repetitions=1):
    c = load_config(config_path)
    if static: c["samples"] = 1
    initialize,run_workbench,doctor = lab_modules(source)
    from enfusion_lab import runner
    root = Path(root).resolve()
    initialize(root)
    prepare(root,c)
    write_json(root/"capture-config.json",c)
    write_json(root/"doctor.json",doctor())
    with private_settings(runner):
        run_workbench(root,"validate",timeout=120)
        for repeat in range(repetitions):
            p,d = camera(c,0)
            run = run_workbench(root,"capture",world=c["world"],position=p,direction=d,
                                settle=c["settle_seconds"],timeout=c["timeout_seconds"])
            try:
                record = verify(c,run)
            except Exception as error:
                write_json(Path(run["directory"])/"sequence.json",{
                    "schema_version":1,"status":"failed","run_id":run["run_id"],
                    "error":str(error),"config":c})
                raise
            record["config_sha256"] = digest(root/"capture-config.json")
            write_json(Path(run["directory"])/"sequence.json",record)
            print(json.dumps({"repeat":repeat+1,"run_id":run["run_id"],"frames":len(record["frames"])}),flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config",default="scenes/arland-motion-v1.json")
    p.add_argument("--root",required=True)
    p.add_argument("--lab-source")
    p.add_argument("--static",action="store_true")
    p.add_argument("--repetitions",type=int,choices=range(1,6),default=1)
    args = p.parse_args()
    capture(args.config,args.root,args.lab_source,args.static,args.repetitions)


if __name__ == "__main__": main()
