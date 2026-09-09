"""Offline GPU processing and a single synchronized comparison video."""
import argparse
import json
from pathlib import Path
import subprocess
import time

import numpy as np
from PIL import Image

from . import model
from .cli import quantize
from .references import digest, write_json


def process(sequence, out, model_path, exe):
    sequence = Path(sequence).resolve()
    manifest = json.loads(sequence.read_text())
    if manifest["status"] != "succeeded": raise ValueError("Unverified capture")
    frames = manifest["frames"]
    if [f["index"] for f in frames] != list(range(len(frames))): raise ValueError("Bad frame order")
    out = Path(out).resolve(); out.mkdir(parents=True,exist_ok=False)
    weights,_ = model.load(model_path)
    (out/"model.hlsl").write_text(model.hlsl(weights),encoding="utf-8")
    report = {"schema_version":1,"status":"running","model_sha256":digest(model_path),
              "shader_sha256":digest(out/"model.hlsl"),"capture_manifest_sha256":digest(sequence),
              "capture_run_id":manifest["run_id"],"dimensions":manifest["dimensions"],
              "playback_fps":manifest["playback_fps"],"frames":[],
              "scope":"One GPU output for each captured source frame. Offline export, processing and retimed playback; not live performance.",
              "scratch":"input.rgba/output.rgba are reused only after that frame passes CPU verification and its PNG/hash/timings are retained."}
    write_json(out/"motion.json",report)
    w,h = manifest["dimensions"]
    started = time.monotonic()
    try:
        for frame in frames:
            source = (sequence.parent/frame["file"]).resolve()
            if not source.is_relative_to(sequence.parent) or digest(source) != frame["sha256"]: raise ValueError("Source frame changed or escaped capture")
            rgba = np.asarray(Image.open(source).convert("RGBA"))
            if rgba.shape != (h,w,4): raise ValueError("Source dimensions changed")
            rgba.tofile(out/"input.rgba")
            i = frame["index"]
            before = time.monotonic()
            timing = out/f"gpu-{i:05d}.json"
            subprocess.run([str(Path(exe).resolve()),str(out/"input.rgba"),str(out/"output.rgba"),str(timing),str(w),str(h),str(out/"model.hlsl"),"0","1"],check=True,timeout=120,stdout=subprocess.DEVNULL)
            gpu = np.fromfile(out/"output.rgba",dtype=np.uint8).reshape(h,w,4)
            expected = quantize(model.infer(rgba[:,:,:3].astype(np.float32)/255,weights))
            maximum = int(np.max(np.abs(gpu[:,:,:3].astype(np.int16)-expected.astype(np.int16))))
            alpha = bool(np.array_equal(gpu[:,:,3],rgba[:,:,3]))
            if maximum > 1 or not alpha: raise ValueError("GPU/CPU mismatch at frame "+str(i))
            output = out/f"output-{i:05d}.png"; Image.fromarray(gpu).save(output)
            report["frames"].append({"index":i,"input_sha256":frame["sha256"],"output_sha256":digest(output),
                    "output":output.name,"rgb_max_error_8bit":maximum,"alpha_exact":alpha,
                    "processing_and_cpu_verification_seconds":time.monotonic()-before,
                    "gpu":json.loads(timing.read_text())})
            write_json(out/"motion.json",report)
            if (i+1)%10 == 0: print(f"Verified {i+1}/{len(frames)} GPU frames",flush=True)
        report["status"] = "succeeded"
    except Exception:
        report["status"] = "failed"; raise
    finally:
        report["total_processing_seconds"] = time.monotonic()-started
        write_json(out/"motion.json",report)
    return report


def video(sequence,out):
    sequence = Path(sequence).resolve(); out = Path(out).resolve()
    capture = json.loads(sequence.read_text()); motion = json.loads((out/"motion.json").read_text())
    if motion["status"] != "succeeded" or motion["capture_manifest_sha256"] != digest(sequence): raise ValueError("Unverified or different processed sequence")
    if len(motion["frames"]) != len(capture["frames"]): raise ValueError("Frame count differs")
    for original,result in zip(capture["frames"],motion["frames"]):
        if original["index"] != result["index"] or digest(sequence.parent/original["file"]) != result["input_sha256"] or digest(out/result["output"]) != result["output_sha256"]: raise ValueError("Pair changed")
    source_dir = (sequence.parent/capture["frames"][0]["file"]).parent
    destination = out/"comparison.mp4"
    fps = str(capture["playback_fps"])
    argv = ["ffmpeg","-hide_banner","-loglevel","error","-n","-framerate",fps,"-i",str(source_dir/"sample-%05d.png"),
            "-framerate",fps,"-i",str(out/"output-%05d.png"),
            "-filter_complex","[0:v]scale=1920:1080:flags=lanczos,setsar=1[a];[1:v]scale=1920:1080:flags=lanczos,setsar=1[b];[a][b]hstack=inputs=2[v]",
            "-map","[v]","-frames:v",str(len(capture["frames"])),"-an","-c:v","libx264","-preset","slow","-crf","16","-pix_fmt","yuv420p","-movflags","+faststart",str(destination)]
    subprocess.run(argv,check=True,timeout=300)
    result = subprocess.run(["ffprobe","-v","error","-count_frames","-show_streams","-of","json",str(destination)],check=True,capture_output=True,text=True)
    streams = json.loads(result.stdout)["streams"]
    if len(streams) != 1: raise ValueError("Unexpected video streams")
    stream = streams[0]
    if stream["codec_name"] != "h264" or [stream["width"],stream["height"]] != [3840,1080] or int(stream["nb_read_frames"]) != len(capture["frames"]) or stream["r_frame_rate"] != fps+"/1": raise ValueError("Encoded video differs from manifest")
    record = {"schema_version":1,"sha256":digest(destination),"bytes":destination.stat().st_size,
              "dimensions":[3840,1080],"frames":len(capture["frames"]),"playback_fps":int(fps),
              "duration_seconds":float(stream["duration"]),"codec":"H.264 / yuv420p / CRF 16",
              "transformation":"Each full frame scaled from 2560x1440 to 1920x1080 with Lanczos; source left, GPU output right, encoded together without interpolation or dropped samples.",
              "capture_manifest_sha256":digest(sequence),"motion_manifest_sha256":digest(out/"motion.json")}
    write_json(out/"video.json",record)
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command",choices=["process","video"]);p.add_argument("--sequence",required=True);p.add_argument("--out",required=True)
    p.add_argument("--model",default="models/bootstrap-v0.json");p.add_argument("--exe",default="build/Release/enr_gpu.exe")
    a = p.parse_args()
    if a.command == "process": process(a.sequence,a.out,a.model,a.exe)
    else: print(json.dumps(video(a.sequence,a.out),indent=2))


if __name__ == "__main__": main()
