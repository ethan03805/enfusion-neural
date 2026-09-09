"""Validate matched renders, fit lighting models on train cases, evaluate all splits.

Requires the references optional dependency (OpenEXR). Test/stress targets are
never passed to training, normalization, baseline fitting or checkpoint selection.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr import lighting
from check_material_room import read_exr

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value): path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
def channels(data,pass_name,suffix): return np.stack([data["ViewLayer."+pass_name+"."+c] for c in suffix],axis=-1)


def load_case(root,run,case):
    data = {}
    for render in case["renders"]:
        role = render["role"]
        for ext in ("exr","png"):
            if sha(root/case["id"]/(role+"."+ext)) != render[ext+"_sha256"]:
                raise ValueError("Changed render: "+case["id"]+"/"+role)
        data[role] = read_exr(root/case["id"]/(role+".exr"))
    source, reference = data["source"],data["reference"]
    geometry = {}
    for name in ("ViewLayer.Depth.Z","ViewLayer.Object Index.X"):
        geometry[name] = bool(np.array_equal(source[name],reference[name]))
    if not all(geometry.values()): raise ValueError("Misaligned geometry: "+case["id"])
    rgb = channels(source,"Combined","RGB"); target = channels(reference,"Combined","RGB")
    position = channels(source,"Position","XYZ"); normal = channels(source,"Normal","XYZ")
    w,h = run["plan"]["dimensions"]
    if rgb.shape != (h,w,3) or target.shape != rgb.shape: raise ValueError("Unexpected dimensions")
    valid = source["ViewLayer.Depth.Z"] < 100
    position[~valid] = 0; normal[~valid] = 0
    cfg = run["base_config"]
    mapping = {obj["id"]:obj["material"] for obj in cfg["boxes"]+cfg["spheres"]}
    mapping.update({"post-"+str(i):cfg["thin_posts"]["material"] for i in range(len(cfg["thin_posts"]["diameters_m"]))})
    materials = np.zeros((max(run["object_ids"].values())+1,5),np.float32)
    for name,index in run["object_ids"].items():
        material = cfg["materials"][mapping[name]]
        materials[index] = material["base_color_linear"]+[material["roughness"],material["metallic"]]
    ids = source["ViewLayer.Object Index.X"].astype(np.int32)
    if ids.min()<0 or ids.max()>=len(materials): raise ValueError("Unknown material ID")
    x = lighting.features(rgb,position,normal,materials[ids],case["camera"],case["light"])
    y = np.log1p(target)-np.log1p(rgb)
    geometry["source_reference_position_max_abs"] = float(np.abs(channels(source,"Position","XYZ")-channels(reference,"Position","XYZ")).max())
    geometry["source_reference_normal_max_abs"] = float(np.abs(channels(source,"Normal","XYZ")-channels(reference,"Normal","XYZ")).max())
    return {"x":x,"y":y,"rgb":rgb,"target":target,"valid":valid,"ids":ids,
            "alpha":source["ViewLayer.Combined.A"],"geometry":geometry,
            "noise":channels(data["noise_check"],"Combined","RGB") if "noise_check" in data else None}


def metric(value,target,mask=None):
    if mask is not None:
        value,target = value[mask],target[mask]
    delta = value.astype(np.float64)-target
    log_delta = np.log1p(value.astype(np.float64))-np.log1p(target)
    return {"linear_mae":float(np.abs(delta).mean()),"linear_rmse":float(np.sqrt(np.mean(delta**2))),
            "relative_linear_rmse":float(np.sqrt(np.mean(delta**2))/max(np.sqrt(np.mean(target.astype(np.float64)**2)),1e-12)),
            "log1p_rmse":float(np.sqrt(np.mean(log_delta**2)))}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("--root",required=True); p.add_argument("--out",required=True)
    a = p.parse_args(); root = Path(a.root).resolve(); out = Path(a.out).resolve(); out.mkdir(parents=True,exist_ok=False)
    run = json.loads((root/"run.json").read_text()); plan = run["plan"]
    if run["status"] != "succeeded" or run["plan_sha256"] != sha(ROOT/"scenes/lighting-study-v1.json"):
        raise ValueError("Incomplete or incompatible data manifest")
    if len(run["cases"]) != len(plan["cases"]): raise ValueError("Missing cases")
    for case,planned in zip(run["cases"],plan["cases"]):
        if any(case[k] != planned[k] for k in planned): raise ValueError("Case definition changed")
        roles = {r["role"]:r for r in case["renders"]}
        if len(roles) != len(case["renders"]) or not {"source","reference"} <= roles.keys(): raise ValueError("Invalid render roles")
        if any(r["samples"] != plan["samples"] for r in roles.values()): raise ValueError("Sample count confound")
        for role in ("source","reference"):
            if roles[role]["seed"] != plan["seed"] or roles[role]["diffuse_bounces"] != plan[role+"_diffuse_bounces"]:
                raise ValueError("Invalid paired transport controls")
    report = {"schema_version":1,"status":"running","scope":plan["scope"],"renderer_run_sha256":sha(root/"run.json"),
              "plan_sha256":run["plan_sha256"],"trainer_sha256":sha(__file__),"model_code_sha256":sha(ROOT/"enr/lighting.py"),
              "feature_names":lighting.FEATURES,"source_data_only_features":True,"training":plan["training"],
              "models":{},"cases":[],"limitations":plan["limitations"]+["CPU lighting inference only; no native GPU cost or live integration result", "No independent scene-family test or temporal sequence"]}
    write(out/"run.json",report)
    cached = {}
    pools = {"train":[],"validation":[]}
    rng = np.random.default_rng(plan["training"]["seed"])
    for case in run["cases"]:
        d = load_case(root,run,case); cached[case["id"]] = d
        if case["split"] in pools:
            candidates = np.flatnonzero(d["valid"])
            count = min(len(candidates),plan["training"]["pixels_per_case"])
            indices = rng.choice(candidates,count,replace=False)
            pools[case["split"]].append((d["x"].reshape(-1,len(lighting.FEATURES))[indices],d["y"].reshape(-1,3)[indices]))
    tx,ty = (np.concatenate([v[i] for v in pools["train"]]) for i in range(2))
    vx,vy = (np.concatenate([v[i] for v in pools["validation"]]) for i in range(2))
    report["training_pixel_count"], report["validation_pixel_count"] = len(tx),len(vx)
    models = {}
    for name,columns in (("scene",len(lighting.FEATURES)),("rgb",3)):
        start = time.perf_counter()
        model = lighting.fit(tx[:,:columns],ty,vx[:,:columns],vy,plan["training"],
            lambda entry:print(json.dumps({"model":name,**entry}),flush=True))
        elapsed = time.perf_counter()-start; models[name] = model
        lighting.save(out/(name+"-model.json"),model,{"plan_sha256":run["plan_sha256"],"selected_step":model["selected_step"],
            "seed":plan["training"]["seed"],"scene_group":plan["scene_group"],"scope":plan["scope"],
            "train_cases":[c["id"] for c in run["cases"] if c["split"] == "train"],
            "validation_cases":[c["id"] for c in run["cases"] if c["split"] == "validation"]})
        restored,_ = lighting.load(out/(name+"-model.json"))
        if not np.array_equal(lighting.predict(vx[:16,:columns],model),lighting.predict(vx[:16,:columns],restored)):
            raise ValueError("Saved lighting model changed inference")
        model_record = {"architecture":f"{columns}-32-32-3 ReLU MLP; 0.25*tanh log-radiance residual",
                        "parameters":sum(w.size for w in model["weights"].values()),"features":lighting.FEATURES[:columns],
                        "selected_step":model["selected_step"],"history":model["history"],"training_seconds":elapsed,
                        "weights_sha256":sha(out/(name+"-model.json")),"backend":"CPU NumPy float32"}
        report["models"][name] = model_record; write(out/"run.json",report)
    # A low-cost affine baseline gets the same scene features and training pixels.
    design = np.column_stack([tx,np.ones(len(tx))]).astype(np.float64)
    regularizer = np.eye(design.shape[1])*1e-3; regularizer[-1,-1] = 0
    affine = np.linalg.solve(design.T@design+regularizer,design.T@ty)
    np.save(out/"affine.npy",affine)
    for case in run["cases"]:
        d = cached[case["id"]]; folder = out/case["id"]; folder.mkdir()
        x = d["x"].reshape(-1,len(lighting.FEATURES)); base = np.log1p(d["rgb"])
        predictions = {"source":d["rgb"],"affine":np.maximum(np.expm1(base+np.clip(np.column_stack([x,np.ones(len(x))])@affine,-lighting.LIMIT,lighting.LIMIT).reshape(base.shape)),0)}
        timings = {}
        for name,model in models.items():
            start = time.perf_counter()
            residual = lighting.predict(x[:,:len(model["mean"])] ,model).reshape(base.shape)
            predictions[name] = np.maximum(np.expm1(base+residual),0)
            timings[name] = (time.perf_counter()-start)*1000
        for name in predictions:
            predictions[name][~d["valid"]] = d["rgb"][~d["valid"]]
        edges = np.zeros(d["valid"].shape,bool)
        edges[1:] |= d["ids"][1:] != d["ids"][:-1]; edges[:-1] |= d["ids"][1:] != d["ids"][:-1]
        edges[:,1:] |= d["ids"][:,1:] != d["ids"][:,:-1]; edges[:,:-1] |= d["ids"][:,1:] != d["ids"][:,:-1]
        post_ids = [value for name,value in run["object_ids"].items() if name.startswith("post-")]
        masks = {"all":None,"surfaces":d["valid"],"object_edges":edges,"thin_posts":np.isin(d["ids"],post_ids)}
        entry = {"id":case["id"],"split":case["split"],"geometry":d["geometry"],
                 "metrics":{name:{region:metric(pred,d["target"],mask) for region,mask in masks.items()} for name,pred in predictions.items()},
                 "cpu_inference_ms_excludes_features_and_io":timings,"outputs":{}}
        if d["noise"] is not None: entry["reference_seed_difference"] = metric(d["noise"],d["target"])
        for name,pred in {**predictions,"reference":d["target"]}.items():
            rgba = np.concatenate([pred,d["alpha"][...,None]],axis=-1).astype(np.float32)
            path = folder/(name+".npy"); np.save(path,rgba)
            entry["outputs"][name] = {"linear_rgba_sha256":sha(path)}
        report["cases"].append(entry); write(out/"run.json",report)
    report["status"] = "succeeded"; write(out/"run.json",report)
    print(json.dumps({"out":str(out),"test":[{"id":c["id"],"rmse":{k:v["all"]["log1p_rmse"] for k,v in c["metrics"].items()}} for c in report["cases"] if c["split"] in ("test","stress")]},indent=2))


if __name__ == "__main__": main()
