"""Check display conversion and retain portable metrics/provenance for every case."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from train_lighting_study import channels, metric
from check_material_room import read_exr

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return np.array(Image.open(path).convert("RGBA"))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",required=True);p.add_argument("--renders",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();root,renders=Path(a.root),Path(a.renders)
    run=json.loads((root/"run.json").read_text());render=json.loads((renders/"run.json").read_text())
    if run["status"] != "succeeded" or run["renderer_run_sha256"] != sha(renders/"run.json"):
        raise ValueError("Incomplete or mismatched study")
    run["display"]=json.loads((root/"display.json").read_text())
    run["rendering"]=render
    run["summarizer_sha256"]=sha(__file__)
    run["model_files"]={name:sha(root/(name+"-model.json")) for name in run["models"]}
    run["affine_weights_sha256"]=sha(root/"affine.npy")
    for case in run["cases"]:
        folder=root/case["id"]
        target=read(renders/case["id"]/"reference.png")
        source=read(renders/case["id"]/"source.png")
        for name in ("source","reference"):
            original=read(renders/case["id"]/(name+".png"));converted=read(folder/(name+".png"))
            delta=np.abs(original.astype(np.int16)-converted.astype(np.int16))
            case.setdefault("display_roundtrip",{})[name]={"rgba_max_error_8bit":int(delta.max()),"rgba_mae_8bit":float(delta.mean())}
            if delta.max()>1: raise ValueError("Display conversion failed: "+case["id"]+"/"+name)
        for name,record in case["outputs"].items():
            path=folder/(name+".png");actual=read(path)
            if not np.array_equal(actual[:,:,3],source[:,:,3]): raise ValueError("Output alpha changed")
            delta=actual[:,:,:3].astype(np.float64)-target[:,:,:3]
            record.update({"png_sha256":sha(path),"bytes":path.stat().st_size,"dimensions":[actual.shape[1],actual.shape[0]],
                           "rgb_mae_8bit":float(np.abs(delta).mean()),"rgb_rmse_8bit":float(np.sqrt(np.mean(delta**2))),"alpha_exact":True})
        noise=renders/case["id"]/"noise_check.png"
        if noise.exists():
            noise_display=read(noise)[:,:,:3]
            delta=noise_display.astype(np.float64)-target[:,:,:3]
            case["reference_seed_difference"]["display_rgb_mae_8bit"]=float(np.abs(delta).mean())
            independent=channels(read_exr(renders/case["id"]/"noise_check.exr"),"Combined","RGB")
            case["independent_reference_metrics"]={}
            for name in case["metrics"]:
                value=np.load(folder/(name+".npy"),allow_pickle=False)[:,:,:3]
                item=metric(value,independent)
                item["display_rgb_mae_8bit"]=float(np.abs(read(folder/(name+".png"))[:,:,:3].astype(np.float64)-noise_display).mean())
                case["independent_reference_metrics"][name]=item
    test=[c for c in run["cases"] if c["split"] == "test"]
    run["held_out_summary"]={name:{"mean_display_rgb_mae_8bit":float(np.mean([c["outputs"][name]["rgb_mae_8bit"] for c in test])),
        "mean_log1p_rmse":float(np.mean([c["metrics"][name]["all"]["log1p_rmse"] for c in test]))} for name in ("source","affine","rgb","scene")}
    run["render_timing_summary"]={role:{"all_cases_median_seconds":float(np.median([r["seconds"] for c in render["cases"] for r in c["renders"] if r["role"]==role])),
        "after_first_case_median_seconds":float(np.median([r["seconds"] for c in render["cases"][1:] for r in c["renders"] if r["role"]==role]))} for role in ("source","reference")}
    run["acceptance"]={"paired_depth_and_ids_exact":True,"display_roundtrip_within_one_code_value":True,
        "all_output_alpha_exact":True,"scene_model_beats_identity_on_each_held_out_case":all(c["outputs"]["scene"]["rgb_mae_8bit"]<c["outputs"]["source"]["rgb_mae_8bit"] for c in test),
        "independent_scene_generalization_verified":False,"temporal_fidelity_verified":False,"net_engine_frame_savings_verified":False}
    Path(a.out).write_text(json.dumps(run,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"held_out":run["held_out_summary"],"render_timing":run["render_timing_summary"],
        "case_display":[{"id":c["id"],"mae":{k:v["rgb_mae_8bit"] for k,v in c["outputs"].items()}} for c in run["cases"] if c["split"] in ("test","stress")],"acceptance":run["acceptance"]},indent=2))


if __name__=="__main__":main()
