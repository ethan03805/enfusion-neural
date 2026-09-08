"""Versioned scene preparation, Enfusion Lab capture and repeatability analysis."""
import argparse
from datetime import date
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import shutil
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def number(value, low, high, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError("Invalid " + label)
    return value


def load_pack(path):
    pack = json.loads(Path(path).read_text(encoding="utf-8"))
    if pack.get("schema_version") != 1 or not re.fullmatch(r"[a-z0-9-]+", pack.get("pack_id", "")):
        raise ValueError("Unsupported scene pack")
    if not re.fullmatch(r"[A-Za-z0-9_./-]+\.ent", pack["world"]) or ".." in pack["world"].split("/"):
        raise ValueError("Invalid world resource")
    defaults = pack["defaults"]
    date(*defaults["date"])
    number(defaults["settle_seconds"], 0.1, 60, "settle")
    number(defaults["timeout_seconds"], 1, 600, "timeout")
    number(defaults["wind_speed_mps"], 0, 50, "wind speed")
    number(defaults["wind_direction_degrees"], 0, 359.999, "wind direction")
    number(defaults["repetitions"], 3, 20, "repetitions")
    if not isinstance(defaults["repetitions"], int):
        raise ValueError("Repetitions must be an integer")
    if not re.fullmatch(r"[A-Za-z0-9_ -]+", defaults["weather_state"]):
        raise ValueError("Invalid weather identifier")
    acceptance = pack["acceptance"]
    for key in ("position_tolerance_m", "direction_tolerance", "hour_tolerance", "wind_tolerance_mps"):
        number(acceptance[key], 0, 1, key)
    radius = acceptance["alignment_search_radius_pixels"]
    if not isinstance(radius, int) or isinstance(radius, bool) or not 1 <= radius <= 16:
        raise ValueError("Alignment radius must be an integer from 1 to 16")
    if acceptance["require_identical_dimensions"] is not True or acceptance["pixel_equality_required"] is not False:
        raise ValueError("This analyzer requires matching dimensions and reports pixel differences without an equality gate")
    ids, groups = set(), {}
    if not pack["scenes"]:
        raise ValueError("Scene pack is empty")
    for scene in pack["scenes"]:
        name = scene["id"]
        if not re.fullmatch(r"[a-z0-9-]+", name) or name in ids:
            raise ValueError("Invalid or duplicated scene id")
        ids.add(name)
        if scene["split"] not in {"diagnostic", "train", "validation", "test"}:
            raise ValueError("Unknown dataset split")
        previous = groups.setdefault(scene["group"], scene["split"])
        if previous != scene["split"]:
            raise ValueError("Overlapping scene group crosses dataset splits")
        number(scene["hour"], 0, 23.999, "hour")
        for key in ("position", "direction"):
            if len(scene[key]) != 3:
                raise ValueError("Camera vectors require three components")
            for v in scene[key]:
                number(v, -1e6, 1e6, key)
        length = math.hypot(*scene["direction"])
        if length == 0:
            raise ValueError("Camera direction is zero")
    return pack


def scene_config(pack, scene):
    values = pack["defaults"]
    year, month, day = values["date"]
    return f'''#ifdef WORKBENCH
class ENR_ReferenceConfig
{{
 static int Year = {year};
 static int Month = {month};
 static int Day = {day};
 static float Hour = {scene['hour']};
 static float WindSpeed = {values['wind_speed_mps']};
 static float WindDirection = {values['wind_direction_degrees']};
 static string Weather = "{values['weather_state']}";
}}
#endif
'''


def prepare(pack_path, scene_id, project):
    pack = load_pack(pack_path)
    scene = next((s for s in pack["scenes"] if s["id"] == scene_id), None)
    if scene is None:
        raise ValueError("Scene is not in pack")
    project = Path(project).resolve()
    if not (project / "enfusion-lab.json").is_file() or not (project / "addon/addon.gproj").is_file():
        raise ValueError("Initialize a dedicated Enfusion Lab project first")
    if (project / ".enfusion-lab.lock").exists():
        raise ValueError("Project is in use")
    game_scripts = project / "addon/Scripts/Game"
    if not game_scripts.resolve().is_relative_to(project):
        raise ValueError("Addon directory escapes project")
    adapter = game_scripts / "ELab_GameCapture.c"
    if adapter.exists():
        text = adapter.read_text(encoding="utf-8")
        if "Batch capture timing is tied" not in text and "Project-owned extension of Enfusion Lab" not in text:
            raise ValueError("Refusing to overwrite an unrecognized capture adapter")
    shutil.copyfile(ROOT / "adapters/enfusion/ELab_GameCapture.c", adapter)
    config = game_scripts / "ENR_ReferenceConfig.c"
    config.write_text(scene_config(pack, scene), encoding="utf-8")
    record = {"schema_version": 1, "pack_id": pack["pack_id"], "pack_sha256": digest(pack_path),
              "scene_id": scene_id, "adapter_sha256": digest(adapter), "config_sha256": digest(config)}
    write_json(project / "reference.json", record)
    return record


def environment_events(path):
    result = {}
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if "ENR {" not in line:
            continue
        event = json.loads(line[line.index("ENR {")+4:])
        result[event["event"]] = event
    return result


def image_metrics(left, right, radius=3):
    if left.shape != right.shape or left.ndim != 3 or left.shape[2] != 4:
        raise ValueError("Repeat images must have identical RGBA dimensions")
    diff = right.astype(np.float32) - left.astype(np.float32)
    rgb = diff[:, :, :3]
    mse = float(np.mean(rgb**2))
    result = {"rgb_mae_8bit": float(np.mean(np.abs(rgb))), "rgb_rmse_8bit": math.sqrt(mse),
              "rgb_p95_absolute_error_8bit": float(np.percentile(np.abs(rgb), 95)),
              "changed_rgb_fraction": float(np.mean(np.any(rgb != 0, axis=2))),
              "alpha_exact": bool(np.array_equal(left[:, :, 3], right[:, :, 3])),
              "mean_rgb_drift_8bit": rgb.mean(axis=(0, 1)).tolist(),
              "psnr_db": None if mse == 0 else float(10*math.log10(255**2/mse))}
    # Estimate integer translation from image gradients. This is not engine motion.
    h, w = left.shape[:2]
    border = radius + 2
    if min(h, w) <= border*2:
        result["alignment"] = {"available": False, "reason": "image too small"}
        return result
    def edges(image):
        gray = image[:, :, :3].astype(np.float32) @ np.array([.2126, .7152, .0722], np.float32)
        gy, gx = np.gradient(gray)
        return np.stack((gx, gy), axis=2)
    a, b = edges(left), edges(right)
    reference = a[border:h-border:4, border:w-border:4]
    variance = float(np.mean(reference**2))
    if variance < 1e-6:
        result["alignment"] = {"available": False, "reason": "insufficient edge structure"}
        return result
    scores = []
    for dy in range(-radius, radius+1):
        for dx in range(-radius, radius+1):
            candidate = b[border+dy:h-border+dy:4, border+dx:w-border+dx:4]
            scores.append((float(np.mean((reference-candidate)**2)), dx, dy))
    scores.sort(key=lambda s: (s[0], abs(s[1])+abs(s[2])))
    score, dx, dy = scores[0]
    zero = next(s[0] for s in scores if s[1:] == (0, 0))
    result["alignment"] = {"available": True, "estimated_translation_px": [dx, dy],
        "sign_convention": "reference(x,y) corresponds to repeat(x+dx,y+dy)",
        "search_radius_px": radius, "search_boundary": abs(dx)==radius or abs(dy)==radius,
        "edge_mse": score, "zero_offset_edge_mse": zero,
        "improvement_fraction": (zero-score)/max(zero, 1e-12),
        "method": "integer gradient matching on a fixed interior ROI, every fourth pixel"}
    return result


def analyze(pack_path, batch_path, output):
    pack = load_pack(pack_path)
    batch_path = Path(batch_path).resolve()
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    if batch["pack_sha256"] != digest(pack_path) or batch["status"] != "succeeded":
        raise ValueError("Batch is incomplete or belongs to a different pack revision")
    if len(batch["runs"]) != len(pack["scenes"]) * pack["defaults"]["repetitions"]:
        raise ValueError("Batch contains an unexpected number of captures")
    output = Path(output)
    if output.exists():
        raise ValueError("Report already exists")
    report = {"schema_version": 1, "pack_id": pack["pack_id"], "pack_sha256": digest(pack_path),
              "scope": "repeatability observations, not photorealistic ground truth",
              "installation_builds": batch.get("installation_builds"), "scenes": []}
    seen = set()
    for scene in pack["scenes"]:
        entries = [r for r in batch["runs"] if r["scene_id"] == scene["id"]]
        if len(entries) != pack["defaults"]["repetitions"]:
            raise ValueError("Batch does not contain the required repeats for " + scene["id"])
        images, captures, contracts = [], [], []
        for entry in entries:
            directory = (batch_path.parent / entry["directory"]).resolve()
            if not directory.is_relative_to(batch_path.parent):
                raise ValueError("Run escapes batch root")
            run = json.loads((directory / "run.json").read_text(encoding="utf-8"))
            if run["run_id"] in seen or run["status"] != "succeeded" or run["command"] != "capture":
                raise ValueError("Duplicate or unverified capture")
            seen.add(run["run_id"])
            if run["world"] != pack["world"]:
                raise ValueError("Capture belongs to a different world")
            telemetry = environment_events(directory / "console.log")
            environment = telemetry["environment"]
            d = pack["defaults"]
            tolerance = pack["acceptance"]
            if environment["date"] != d["date"] or environment["weather_state"] != d["weather_state"]:
                raise ValueError("Observed environment does not match scene")
            for key, expected, limit in [("hour", scene["hour"], tolerance["hour_tolerance"]), ("wind_speed_mps", d["wind_speed_mps"], tolerance["wind_tolerance_mps"]), ("wind_direction_degrees", d["wind_direction_degrees"], .01)]:
                value = environment[key]
                if not math.isfinite(value) or abs(value-expected) > limit:
                    raise ValueError("Environment mismatch: " + key)
            camera = next(e for e in run["events"] if e["event"] == "camera")
            direction = np.array(scene["direction"]) / math.hypot(*scene["direction"])
            for key, expected, limit in [("position", scene["position"], tolerance["position_tolerance_m"]), ("direction", direction, tolerance["direction_tolerance"])]:
                if not np.isfinite(camera[key]).all() or not np.allclose(camera[key], expected, atol=limit, rtol=0):
                    raise ValueError("Camera mismatch: " + key)
            if camera["elapsed_simulation_seconds"] < d["settle_seconds"]:
                raise ValueError("Screenshot was requested before the settle interval")
            image_path = directory / "frame.png"
            if digest(image_path) != run["image"]["sha256"]:
                raise ValueError("Image changed since capture")
            with Image.open(image_path) as image:
                if list(image.size) != [run["image"]["width"], run["image"]["height"]]:
                    raise ValueError("Image dimensions disagree with capture manifest")
                images.append(np.asarray(image.convert("RGBA")))
            contracts.append(run["addon_sha256"])
            captures.append({"run_id": run["run_id"], "image_sha256": run["image"]["sha256"],
                "dimensions": [run["image"]["width"], run["image"]["height"]], "camera": camera,
                "environment": environment, "exposure": telemetry.get("exposure")})
        if any(contract != contracts[0] for contract in contracts):
            raise ValueError("Addon changed between repetitions")
        pairs = [{"left": i+1, "right": j+1, **image_metrics(images[i], images[j], pack["acceptance"]["alignment_search_radius_pixels"])}
                 for i, j in itertools.combinations(range(len(images)), 2)]
        report["scenes"].append({"id": scene["id"], "group": scene["group"], "split": scene["split"],
            "controls_verified": True, "addon_sha256": contracts[0], "captures": captures, "pairs": pairs,
            "render_settings": d["render_settings"]})
    write_json(output, report)
    return report


def lab_modules(source):
    if source:
        source = Path(source).resolve()
        if not (source / "enfusion_lab/runner.py").is_file():
            raise ValueError("--lab-source must point to an Enfusion Lab checkout/package root")
        sys.path.insert(0, str(source))
    try:
        from enfusion_lab.config import initialize
        from enfusion_lab.runner import run_workbench
        from enfusion_lab.cli import doctor
    except ImportError as error:
        raise ValueError("Install Enfusion Lab separately or provide --lab-source") from error
    return initialize, run_workbench, doctor


def capture_batch(pack_path, root, source):
    pack = load_pack(pack_path)
    initialize, run_workbench, doctor = lab_modules(source)
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    detected = doctor()
    if not detected["workbench_available"]:
        raise ValueError("Stable Workbench is unavailable")
    write_json(root / "doctor.json", detected)
    batch = {"schema_version": 1, "pack_id": pack["pack_id"], "pack_sha256": digest(pack_path),
             "status": "running", "installation_builds": {key: value["buildid"] for key, value in detected["steam"].items()},
             "runs": []}
    write_json(root / "batch.json", batch)
    try:
        for scene in pack["scenes"]:
            project = root / scene["id"]
            initialize(project)
            prepare(pack_path, scene["id"], project)
            run_workbench(project, "validate", timeout=pack["defaults"]["timeout_seconds"])
            for repeat in range(pack["defaults"]["repetitions"]):
                run = run_workbench(project, "capture", world=pack["world"], position=scene["position"],
                    direction=scene["direction"], settle=pack["defaults"]["settle_seconds"], timeout=pack["defaults"]["timeout_seconds"])
                batch["runs"].append({"scene_id": scene["id"], "directory": str(Path(run["directory"]).relative_to(root))})
                write_json(root / "batch.json", batch)
                print(f"{scene['id']} repeat {repeat+1}: {run['status']}", flush=True)
        batch["status"] = "succeeded"
    except Exception as error:
        batch["status"] = "failed"
        batch["error"] = str(error)
        raise
    finally:
        write_json(root / "batch.json", batch)
    return analyze(pack_path, root / "batch.json", root / "repeatability.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", default="scenes/arland-reference-v1.json")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare"); p.add_argument("--scene", required=True); p.add_argument("--project", required=True)
    p = sub.add_parser("capture"); p.add_argument("--root", required=True); p.add_argument("--lab-source")
    p = sub.add_parser("analyze"); p.add_argument("--batch", required=True); p.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(args.pack, args.scene, args.project)
        elif args.command == "capture":
            result = capture_batch(args.pack, args.root, args.lab_source)
        else:
            result = analyze(args.pack, args.batch, args.out)
        if "scenes" in result:
            print(json.dumps({"pack_id": result["pack_id"], "scenes": len(result["scenes"]),
                              "comparisons": sum(len(s["pairs"]) for s in result["scenes"]),
                              "report": args.out if args.command == "analyze" else str(Path(args.root)/"repeatability.json")}, indent=2))
        else:
            print(json.dumps(result, indent=2, allow_nan=False))
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
