"""Evaluate frozen lighting models on original camera/light paths. Never fits.

Independent reference seeds are the primary targets. Temporal error changes are
reprojected using source positions, object IDs and normals with explicit masks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr import lighting,temporal
from check_material_room import read_exr
from train_lighting_study import channels,metric

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")


def load_frame(folder,frame,sequence,plan):
    data={}
    if len(frame["renders"])!=3 or {r["role"] for r in frame["renders"]}!={"source","reference","independent"}:
        raise ValueError("Incomplete or repeated render roles")
    for render in frame["renders"]:
        role=render["role"]
        expected_seed=plan["independent_seed" if role=="independent" else "paired_seed"]+frame["index"]*plan["seed_stride"]
        expected_bounces=plan["source_diffuse_bounces" if role=="source" else "reference_diffuse_bounces"]
        if (render["seed"]!=expected_seed or render["diffuse_bounces"]!=expected_bounces or render["samples"]!=plan["samples"]):
            raise ValueError("Render controls differ from the frozen plan")
        for extension in ("png","exr"):
            if sha(folder/(role+"."+extension))!=render[extension+"_sha256"]:raise ValueError("Changed render")
        data[role]=read_exr(folder/(role+".exr"))
    source,paired,target=data["source"],data["reference"],data["independent"]
    geometry={name:bool(np.array_equal(source[name],paired[name])) for name in ("ViewLayer.Depth.Z","ViewLayer.Object Index.X")}
    if not all(geometry.values()):raise ValueError("Paired geometry differs")
    ids=source["ViewLayer.Object Index.X"].astype(np.int32);valid=(ids>0)&(source["ViewLayer.Depth.Z"]<100)
    position=channels(source,"Position","XYZ");normal=channels(source,"Normal","XYZ")
    position[~valid]=0;normal[~valid]=0
    rgb=channels(source,"Combined","RGB");h,w=ids.shape
    if [w,h]!=plan["dimensions"]:raise ValueError("Unexpected frame dimensions")
    material=np.zeros((max(o["id"] for o in sequence["objects"].values())+1,5),np.float32)
    for obj in sequence["objects"].values():
        mat=sequence["config"]["materials"][obj["material"]]
        material[obj["id"]]=mat["base_color_linear"]+[mat["roughness"],mat["metallic"]]
    if ids.min()<0 or ids.max()>=len(material):raise ValueError("Unrecognized object")
    x=lighting.features(rgb,position,normal,material[ids],frame["camera"],frame["light"])
    xy,_=temporal.project(position,frame["camera_matrix"],plan["vertical_fov_degrees"])
    yy,xx=np.indices(ids.shape);inside=temporal.interior(ids)
    projection_error=np.linalg.norm(xy-np.stack([xx,yy],axis=-1),axis=-1)[inside]
    p95=float(np.quantile(projection_error,.95))
    if p95>1:raise ValueError("Camera projection does not match source positions")
    geometry["self_projection_p95_pixels"]=p95
    return {"x":x,"rgb":rgb,"target":channels(target,"Combined","RGB"),"paired":channels(paired,"Combined","RGB"),
            "position":position,"normal":normal,"ids":ids,"valid":valid,"alpha":source["ViewLayer.Combined.A"],"geometry":geometry}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--root",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();root=Path(a.root).resolve();out=Path(a.out).resolve()
    run=json.loads((root/"run.json").read_text());plan=run["plan"]
    if run["status"]!="succeeded" or run["plan_sha256"]!=sha(ROOT/"scenes/lighting-motion-v1.json"):
        raise ValueError("Incomplete or changed motion plan")
    if len(run["sequences"])!=len(plan["sequences"]):raise ValueError("Missing sequence")
    models={}
    for name,definition in plan["models"].items():
        path=ROOT/definition["path"]
        if sha(path)!=definition["sha256"]:raise ValueError("Frozen model changed")
        models[name]=lighting.load(path)[0]
    affine_record=json.loads((ROOT/"models/lighting-affine-v1.json").read_text())
    if affine_record["source_npy_sha256"]!=plan["affine_source_sha256"] or affine_record["features"]!=lighting.FEATURES+["bias"]:
        raise ValueError("Unexpected affine baseline")
    affine=np.asarray(affine_record["weights"],np.float64)
    if affine.shape!=(21,3) or not np.isfinite(affine).all():raise ValueError("Invalid affine weights")
    # Recreate the original .npy bytes to establish the retained coefficients.
    import io
    buffer=io.BytesIO();np.save(buffer,affine)
    if hashlib.sha256(buffer.getvalue()).hexdigest()!=plan["affine_source_sha256"]:raise ValueError("Affine coefficients changed")
    out.mkdir(parents=True,exist_ok=False)
    report={"schema_version":1,"status":"running","scope":plan["scope"],"plan_sha256":run["plan_sha256"],
            "renderer_run_sha256":sha(root/"run.json"),"evaluator_sha256":sha(__file__),"temporal_code_sha256":sha(ROOT/"enr/temporal.py"),
            "model_code_sha256":sha(ROOT/"enr/lighting.py"),"model_files":plan["models"],"affine_sha256":sha(ROOT/"models/lighting-affine-v1.json"),
            "python":sys.version,"numpy":np.__version__,"training_performed":False,"sequences":[],"cases":[],
            "temporal_definition":"RMSE of (log1p(output)-log1p(independent reference)) minus the previous error reprojected onto the same static surface. Bilinear previous sampling; reject ID, position, normal or screen mismatch. Sampling noise remains.",
            "limitations":plan["limitations"]+["CPU reference only; no GPU or complete-frame performance result","Temporal correspondence excludes boundaries and unmatched surfaces; regional errors are reported separately"]}
    def save():write(out/"run.json",report)
    save()
    try:
        for definition,sequence in zip(plan["sequences"],run["sequences"]):
            temporal.validate_sequence(sequence,definition,plan)
            if sequence["config_sha256"]!=sha(ROOT/"scenes"/definition["scene"]):raise ValueError("Scene configuration changed")
            summary={"id":sequence["id"],"group":sequence["group"],"role":sequence["role"],"case_ids":[]}
            report["sequences"].append(summary);previous=None
            for index,frame in enumerate(sequence["frames"]):
                if frame["index"]!=index:raise ValueError("Nonconsecutive frames")
                folder=root/sequence["id"]/f"{index:04d}"
                d=load_frame(folder,frame,sequence,plan)
                x=d["x"].reshape(-1,20);base=np.log1p(d["rgb"])
                predictions={"source":d["rgb"],"affine":np.maximum(np.expm1(base+np.clip(np.column_stack([x,np.ones(len(x))])@affine,-lighting.LIMIT,lighting.LIMIT).reshape(base.shape)),0)}
                timing={}
                for name,model in models.items():
                    start=time.perf_counter();residual=lighting.predict(x[:,:len(model["mean"])],model).reshape(base.shape)
                    predictions[name]=np.maximum(np.expm1(base+residual),0);timing[name]=(time.perf_counter()-start)*1000
                for value in predictions.values():value[~d["valid"]]=d["rgb"][~d["valid"]]
                ids=d["ids"];edges=(ids>0)&~temporal.interior(ids)
                post_ids=[o["id"] for name,o in sequence["objects"].items() if name.startswith("post-")]
                mark_ids=[o["id"] for name,o in sequence["objects"].items() if name.startswith("mark-")]
                masks={"all":None,"object_edges":edges,"thin_posts":np.isin(ids,post_ids),"markings":np.isin(ids,mark_ids)}
                entry={"id":sequence["id"]+f"-{index:04d}","sequence":sequence["id"],"index":index,"time_seconds":frame["time_seconds"],
                       "geometry":d["geometry"],"cpu_inference_ms_excludes_features_and_io":timing,"outputs":{},
                       "region_pixel_counts":{k:int(v.sum()) if v is not None else ids.size for k,v in masks.items()},
                       "metrics":{name:{region:metric(value,d["target"],mask) if mask is None or mask.any() else None for region,mask in masks.items()} for name,value in predictions.items()},
                       "reference_seed_difference":metric(d["paired"],d["target"])}
                errors={name:np.log1p(value)-np.log1p(d["target"]) for name,value in predictions.items()}
                errors["reference_noise"]=np.log1p(d["paired"])-np.log1p(d["target"])
                if previous is not None:
                    controls=plan["temporal"]
                    xy,mask,coverage=temporal.correspondence(d,previous,previous["camera_matrix"],plan["vertical_fov_degrees"],controls["world_tolerance_m"],controls["normal_dot_min"])
                    if coverage["valid_pixels"]<controls["minimum_valid_pixels"] or coverage["valid_fraction"]<controls["minimum_valid_fraction"]:
                        raise ValueError("Insufficient temporal correspondences")
                    entry["temporal"]={"coverage":coverage,"error_change":{name:temporal.error_change(error,previous["errors"][name],xy,mask) for name,error in errors.items()}}
                    unmatched=temporal.interior(ids)&~mask
                    entry["unmatched_interior_pixels"]=int(unmatched.sum())
                    entry["unmatched_interior_metrics"]={name:metric(value,d["target"],unmatched) if unmatched.any() else None for name,value in predictions.items()}
                if mark_ids:
                    board=ids==sequence["objects"]["mark-board"]["id"]
                    bars=np.isin(ids,[o["id"] for name,o in sequence["objects"].items() if name.startswith("mark-bar-")])
                    def contrast(value):
                        luma=np.log1p(value)@np.array([.2126,.7152,.0722])
                        return float(luma[board].mean()-luma[bars].mean()) if board.any() and bars.any() else None
                    entry["marking_log_luminance_contrast"]={name:contrast(value) for name,value in {**predictions,"reference":d["target"]}.items()}
                destination=out/entry["id"];destination.mkdir()
                for name,value in {**predictions,"reference":d["target"]}.items():
                    path=destination/(name+".npy");np.save(path,np.concatenate([value,d["alpha"][...,None]],-1).astype(np.float32))
                    entry["outputs"][name]={"linear_rgba_sha256":sha(path)}
                previous={k:d[k] for k in ("position","normal","ids")};previous["errors"]=errors;previous["camera_matrix"]=frame["camera_matrix"]
                report["cases"].append(entry);summary["case_ids"].append(entry["id"]);save()
                print("ENR_EVALUATED "+entry["id"],flush=True)
            cases=[c for c in report["cases"] if c["sequence"]==sequence["id"]]
            summary["mean_log1p_rmse"]={name:float(np.mean([c["metrics"][name]["all"]["log1p_rmse"] for c in cases])) for name in predictions}
            summary["mean_temporal_error_rmse"]={name:float(np.mean([c["temporal"]["error_change"][name]["rmse"] for c in cases if "temporal" in c])) for name in errors}
            summary["frame_count"]=len(cases)
            summary["acceptance"]={"mean_spatial_error_below_identity":summary["mean_log1p_rmse"]["scene"]<summary["mean_log1p_rmse"]["source"],
                "mean_temporal_error_below_identity":summary["mean_temporal_error_rmse"]["scene"]<summary["mean_temporal_error_rmse"]["source"]}
            save()
        report["status"]="succeeded"
    except Exception:report["status"]="failed";raise
    finally:save()
    print(json.dumps(report["sequences"],indent=2))


if __name__=="__main__":main()
