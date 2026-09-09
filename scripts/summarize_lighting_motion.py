"""Validate display images and aggregate frozen-model spatial/temporal evidence."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return np.array(Image.open(path).convert("RGBA"))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--root",required=True);p.add_argument("--renders",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();root,renders=Path(a.root),Path(a.renders)
    report=json.loads((root/"run.json").read_text());render=json.loads((renders/"run.json").read_text())
    if report["status"]!="succeeded" or report["renderer_run_sha256"]!=sha(renders/"run.json"):
        raise ValueError("Incomplete or mismatched experiment")
    report["rendering"]=render;report["display"]=json.loads((root/"display.json").read_text());report["summarizer_sha256"]=sha(__file__)
    names=("source","affine","rgb","scene")
    for case in report["cases"]:
        folder=root/case["id"];original=renders/case["sequence"]/f'{case["index"]:04d}'
        target=read(original/"independent.png");source=read(original/"source.png")
        case["display_roundtrip"]={}
        for name,original_name in (("source","source"),("reference","independent")):
            delta=np.abs(read(folder/(name+".png")).astype(np.int16)-read(original/(original_name+".png")).astype(np.int16))
            case["display_roundtrip"][name]={"rgba_max_error_8bit":int(delta.max()),"rgba_mae_8bit":float(delta.mean())}
            if delta.max()>1:raise ValueError("Display conversion mismatch")
        for name,record in case["outputs"].items():
            path=folder/(name+".png");value=read(path)
            if value.shape!=target.shape or not np.array_equal(value[:,:,3],source[:,:,3]):raise ValueError("Display shape or alpha changed")
            delta=value[:,:,:3].astype(np.float64)-target[:,:,:3]
            record.update({"png_sha256":sha(path),"bytes":path.stat().st_size,"dimensions":[value.shape[1],value.shape[0]],
                "rgb_mae_8bit":float(np.abs(delta).mean()),"rgb_rmse_8bit":float(np.sqrt(np.mean(delta**2))),"alpha_exact":True})
        case["reference_seed_difference"]["display_rgb_mae_8bit"]=float(np.abs(read(original/"reference.png")[:,:,:3].astype(np.float64)-target[:,:,:3]).mean())
    for sequence in report["sequences"]:
        cases=[c for c in report["cases"] if c["sequence"]==sequence["id"]]
        sequence["mean_display_rgb_mae_8bit"]={name:float(np.mean([c["outputs"][name]["rgb_mae_8bit"] for c in cases])) for name in names}
        sequence["frames_scene_worse_than_source"]=sum(c["metrics"]["scene"]["all"]["log1p_rmse"]>c["metrics"]["source"]["all"]["log1p_rmse"] for c in cases)
        sequence["temporal_pairs_scene_worse_than_source"]=sum(c["temporal"]["error_change"]["scene"]["rmse"]>c["temporal"]["error_change"]["source"]["rmse"] for c in cases if "temporal" in c)
        sequence["mean_reference_noise_log1p_rmse"]=float(np.mean([c["reference_seed_difference"]["log1p_rmse"] for c in cases]))
        sequence["mean_reference_noise_display_mae_8bit"]=float(np.mean([c["reference_seed_difference"]["display_rgb_mae_8bit"] for c in cases]))
        sequence["temporal_valid_fraction_min_mean_max"]=[float(f([c["temporal"]["coverage"]["valid_fraction"] for c in cases if "temporal" in c])) for f in (np.min,np.mean,np.max)]
        sequence["mean_region_log1p_rmse"]={region:{name:float(np.mean([c["metrics"][name][region]["log1p_rmse"] for c in cases if c["metrics"][name][region] is not None])) for name in names} for region in ("object_edges","thin_posts","markings") if any(c["metrics"]["scene"][region] is not None for c in cases)}
        sequence["region_frames_scene_worse_than_source"]={region:sum(c["metrics"]["scene"][region]["log1p_rmse"]>c["metrics"]["source"][region]["log1p_rmse"] for c in cases if c["metrics"]["scene"][region] is not None) for region in sequence["mean_region_log1p_rmse"]}
        contrasts=[c["marking_log_luminance_contrast"] for c in cases if "marking_log_luminance_contrast" in c]
        if contrasts:
            sequence["mean_absolute_marking_contrast_error"]={name:float(np.mean([abs(c[name]-c["reference"]) for c in contrasts])) for name in names}
        sequence["median_cpu_scene_inference_ms"]=float(np.median([c["cpu_inference_ms_excludes_features_and_io"]["scene"] for c in cases]))
        sequence["publication_case_id"]=sequence["id"]+f'-{render["plan"]["publication_frame"]:04d}'
    report["verification"]={"all_planned_frames_evaluated":len(report["cases"])==sum(len(s["frames"]) for s in render["sequences"]),
        "all_display_roundtrips_within_one_code_value":True,"all_output_alpha_exact":True,"frozen_models":True,
        "no_training_or_selection_on_test_sequences":True,"gameplay_fidelity_verified":False,"live_engine_performance_verified":False}
    # Portable evidence is hashed by the video report: keep LF bytes across Git/OS.
    Path(a.out).write_bytes((json.dumps(report,indent=2,allow_nan=False)+"\n").encode("utf-8"))
    print(json.dumps([{k:v for k,v in s.items() if k!="case_ids"} for s in report["sequences"]],indent=2))


if __name__=="__main__":main()
