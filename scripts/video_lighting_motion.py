"""Encode traceable source/model/independent-reference triptychs without scaling."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from PIL import Image,ImageDraw,ImageFont

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--root",required=True);p.add_argument("--report",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args();root=Path(a.root).resolve();out=Path(a.out).resolve();report=json.loads(Path(a.report).read_text())
    if report["status"]!="succeeded" or not all(report["verification"][k] for k in ("all_display_roundtrips_within_one_code_value","all_output_alpha_exact","frozen_models")):
        raise ValueError("Unverified model sequence")
    out.mkdir(parents=True,exist_ok=False)
    plan=report["rendering"]["plan"];w,h=plan["dimensions"];fps=plan["playback_fps"]
    result={"schema_version":1,"status":"running","report_sha256":sha(a.report),"encoder_sha256":sha(__file__),"videos":[]}
    font=ImageFont.load_default(size=16)
    for sequence in report["sequences"]:
        frames=[c for c in report["cases"] if c["sequence"]==sequence["id"]]
        if [c["index"] for c in frames]!=list(range(plan["frames"])):raise ValueError("Incorrect video frame order")
        folder=out/sequence["id"];folder.mkdir();frame_records=[]
        for case in frames:
            canvas=Image.new("RGB",(w*3,h+32),(23,27,32));draw=ImageDraw.Draw(canvas)
            for i,(name,label) in enumerate((("source","Source"),("scene","Frozen lighting model"),("reference","Independent reference"))):
                path=root/case["id"]/(name+".png")
                if sha(path)!=case["outputs"][name]["png_sha256"]:raise ValueError("Video input image changed")
                with Image.open(path) as image:
                    if image.size!=(w,h):raise ValueError("Image dimensions changed")
                    canvas.paste(image.convert("RGB"),(i*w,32))
                draw.text((i*w+12,6),label,font=font,fill=(226,230,235))
            path=folder/f'frame-{case["index"]:04d}.png';canvas.save(path)
            frame_records.append({"index":case["index"],"sha256":sha(path)})
        destination=out/(sequence["id"]+".mp4")
        command=["ffmpeg","-hide_banner","-loglevel","error","-n","-framerate",str(fps),"-i",str(folder/"frame-%04d.png"),
                 "-frames:v",str(len(frames)),"-an","-c:v","libx264","-preset","slow","-crf","16","-pix_fmt","yuv420p","-movflags","+faststart",str(destination)]
        subprocess.run(command,check=True,timeout=180)
        probe=subprocess.run(["ffprobe","-v","error","-count_frames","-show_streams","-of","json",str(destination)],capture_output=True,text=True,check=True)
        streams=json.loads(probe.stdout)["streams"]
        if len(streams)!=1:raise ValueError("Unexpected video streams")
        stream=streams[0]
        if (stream["codec_name"]!="h264" or [stream["width"],stream["height"]]!=[w*3,h+32] or int(stream["nb_read_frames"])!=len(frames) or stream["r_frame_rate"]!=str(fps)+"/1"):
            raise ValueError("Video dimensions, cadence or frame count mismatch")
        result["videos"].append({"sequence":sequence["id"],"file":destination.name,"sha256":sha(destination),"bytes":destination.stat().st_size,
            "dimensions":[w*3,h+32],"frames":len(frames),"playback_fps":fps,"duration_seconds":float(stream["duration"]),
            "codec":"H.264, yuv420p, CRF 16","transform":"Source, frozen model and independent reference concatenated horizontally at original resolution; 32px label band added above images. H.264 encoding changes pixels. No interpolation, scaling, dropped frames or retiming.",
            "frame_records":frame_records,"poster_frame":plan["publication_frame"],"poster_sha256":frame_records[plan["publication_frame"]]["sha256"]})
        (out/"video.json").write_text(json.dumps(result,indent=2)+"\n")
    result["status"]="succeeded";(out/"video.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps([{k:v for k,v in item.items() if k!="frame_records"} for item in result["videos"]],indent=2))


if __name__=="__main__":main()
