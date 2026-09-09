"""Validate every EXR part, geometry alignment, hashes and reference noise."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from enr.references import digest,image_metrics,write_json


def read_exr(path):
    import OpenEXR
    channels = {}
    with OpenEXR.File(str(path),separate_channels=True) as file:
        for part in file.parts:
            for name,channel in part.channels.items():
                if name in channels: raise ValueError("Duplicate channel")
                channels[name] = channel.pixels.copy()
    required = ["ViewLayer.Combined."+x for x in "RGBA"] + ["ViewLayer.Depth.Z","ViewLayer.Object Index.X"] + ["ViewLayer.Normal."+x for x in "XYZ"]
    if any(name not in channels for name in required): raise ValueError("Missing EXR pass")
    if any(not np.isfinite(channels[name]).all() for name in required): raise ValueError("Nonfinite reference data")
    shapes = {channels[name].shape for name in required}
    if len(shapes) != 1 or len(next(iter(shapes))) != 2:
        raise ValueError("EXR passes have inconsistent dimensions")
    return channels


def analyze(root,out):
    import OpenEXR
    root = Path(root)
    record = json.loads((root/"run.json").read_text())
    if record["status"] != "succeeded" or len(record["renders"]) != 3: raise ValueError("Incomplete reference run")
    if {r["role"] for r in record["renders"]} != {"source","reference","convergence_check"}:
        raise ValueError("Invalid reference roles")
    data,images = {},{}
    for render in record["renders"]:
        role = render["role"]
        for extension in ["png","exr"]:
            if digest(root/(role+"."+extension)) != render[extension+"_sha256"]: raise ValueError("Reference file changed")
        data[role] = read_exr(root/(role+".exr"))
        images[role] = np.array(Image.open(root/(role+".png")).convert("RGBA"))
        width,height = record["config"]["dimensions"]
        if images[role].shape != (height,width,4) or data[role]["ViewLayer.Depth.Z"].shape != (height,width):
            raise ValueError("Reference dimensions differ from scene config")
    a,b,c = data["source"],data["reference"],data["convergence_check"]
    geometry = {}
    for name in ["ViewLayer.Depth.Z","ViewLayer.Object Index.X"]:
        delta = np.abs(a[name].astype(np.float64)-b[name])
        geometry[name] = {"exact":bool(np.array_equal(a[name],b[name])),"max_error":float(delta.max())}
    normal_error = np.stack([a["ViewLayer.Normal."+x]-b["ViewLayer.Normal."+x] for x in "XYZ"],axis=2)
    geometry["normal"] = {"max_absolute_component_error":float(np.abs(normal_error).max()),"mean_absolute_component_error":float(np.abs(normal_error).mean())}
    def rgb(d): return np.stack([d["ViewLayer.Combined."+x] for x in "RGB"],axis=2)
    reference,check = rgb(b),rgb(c)
    relative_rmse = float(np.sqrt(np.mean((reference-check)**2))/max(float(np.sqrt(np.mean(reference**2))),1e-12))
    noise = image_metrics(images["reference"],images["convergence_check"])
    source_metrics = image_metrics(images["source"],images["reference"])
    report = {"schema_version":1,"render_run":record,"openexr_version":OpenEXR.__version__,
              "channels":sorted(a),"geometry_alignment":geometry,
              "source_reference_display_metrics":source_metrics,"reference_seed_display_metrics":noise,
              "reference_seed_linear_relative_rmse":relative_rmse,
              "scope":"Synthetic shared-scene pair; finite-sample path-traced reference, not photographic ground truth or an Enfusion appearance result.",
              "acceptance":{"geometry_depth_and_ids_exact":all(geometry[k]["exact"] for k in ["ViewLayer.Depth.Z","ViewLayer.Object Index.X"]),
                            "reference_noise_display_mae_below_0_5":noise["rgb_mae_8bit"] < .5},
              "source_artifacts":{"blend_sha256":digest(root/"material-room.blend"),"fbx_sha256":digest(root/"material-room.fbx")}}
    write_json(out,report)
    print(json.dumps({"geometry":geometry,"noise_mae":noise["rgb_mae_8bit"],"linear_relative_rmse":relative_rmse,"source_reference_mae":source_metrics["rgb_mae_8bit"]},indent=2))
    if not all(report["acceptance"].values()): raise ValueError("Reference acceptance failed; retained report must remain diagnostic")


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--root",required=True);p.add_argument("--out",required=True);a=p.parse_args();analyze(a.root,a.out)
