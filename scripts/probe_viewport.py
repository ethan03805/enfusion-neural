"""Reproduce viewport-control investigations; no case certifies render scale/FSR."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from enr import sequence
from enr.references import ROOT, digest, lab_modules, write_json

PRESETS = {
    "diag-render-off": '"VSync" 1\n"Render world" 1\n',
    "diag-half-off": '"Resolution scale" 6\n"Override FSR settings" 1\n"  FSR enabled" 0\n',
    "diag-half-on": '"Resolution scale" 6\n"Override FSR settings" 1\n"  FSR enabled" 1\n',
}
CASES = tuple(PRESETS) + ("workspace-quarter", "texture-export")


def prepare(root, config, case):
    sequence.prepare(root, config)
    if case in PRESETS:
        (root / "addon/ENR_Diag.txt").write_text(PRESETS[case], encoding="utf-8")
        return
    game = root / "addon/Scripts/Game/ELab_GameCapture.c"
    text = game.read_text(encoding="utf-8")
    if case == "workspace-quarter":
        text = text.replace("ENR_Sequence.Camera(world);", """ENR_Sequence.Camera(world);
  if (ELab_CaptureState.Elapsed > 2)
  {
   WorkspaceWidget ws = GetGame().GetWorkspace();
   ws.SetResolutionScale(0.25);
   ws.ToggleFSR(false);
  }""")
        text = text.replace("ELab_CaptureState.Armed = false;\n  vector camera", """WorkspaceWidget captureWorkspace = GetGame().GetWorkspace();
  int nw, nh, rw, rh;
  System.GetNativeResolution(nw, nh);
  System.GetRenderingResolution(rw, rh);
  PrintFormat("ENR_WS workspace=%1x%2 native=%3x%4 rendering=%5x%6 scale=%7 fsr=%8", captureWorkspace.GetWidth(), captureWorkspace.GetHeight(), nw, nh, rw, rh, captureWorkspace.GetResolutionScale(), captureWorkspace.IsFSREnabled());
  ELab_CaptureState.Armed = false;
  vector camera""")
    else:
        source = ROOT / "adapters/enfusion/probes/ENR_RenderTargetProbe.c"
        (root / "addon/Scripts/Game/ENR_RenderTargetProbe.c").write_bytes(source.read_bytes())
        text = text.replace("ENR_Sequence.Camera(world);", "ENR_Sequence.Camera(world); ENR_RenderTargetProbe.Init(world);")
        text = text.replace("if (!ENR_Sequence.Tick(world, width, height)) return;", """ENR_RenderTargetProbe.Export();
  if (!ENR_Sequence.Tick(world, width, height)) { return; }
  if (!ENR_RenderTargetProbe.Completed) { return; }""")
    game.write_text(text, encoding="utf-8")


def capture(root, case, source):
    initialize, run_workbench, doctor = lab_modules(source)
    from enfusion_lab import runner
    root = Path(root).resolve()
    config = sequence.load_config(ROOT / "scenes/arland-motion-v1.json")
    config["samples"] = 1
    initialize(root)
    prepare(root, config, case)
    write_json(root / "doctor.json", doctor())
    write_json(root / "capture-config.json", config)
    with sequence.private_settings(runner):
        run_workbench(root, "validate", timeout=120)
        position, direction = sequence.camera(config, 0)
        run = run_workbench(root, "capture", world=config["world"], position=position,
                            direction=direction, settle=config["settle_seconds"], timeout=config["timeout_seconds"])
    directory = Path(run["directory"])
    report = {"schema_version": 1, "case": case, "run_id": run["run_id"],
              "capture_status": run["status"], "viewport_scale_verified": False,
              "viewport_fsr_verified": False, "addon_sha256": run["addon_sha256"],
              "limits": ["Capture success is not success of the control or export probe.",
                         "These diagnostic cases are not training captures or performance measurements."]}
    try:
        sequence_report = sequence.verify(config, run)
    except ValueError as error:
        sequence_report = {"status": "failed", "error": str(error)}
    write_json(directory / "sequence.json", sequence_report)
    report["sequence_contract"] = {k: sequence_report[k] for k in ("status", "error") if k in sequence_report}
    lines = (directory / "console.log").read_text(encoding="utf-8", errors="replace").splitlines()
    report["probe_telemetry"] = [line.split("SCRIPT", 1)[-1].lstrip(" :") for line in lines if "ENR_RT " in line or "ENR_WS " in line]
    texture = directory / "profile/profile/render-target.png"
    report["texture_file_present"] = texture.is_file()
    if texture.is_file():
        from PIL import Image
        with Image.open(texture) as image:
            dimensions = list(image.size)
            image.verify()
        report["texture"] = {"dimensions": dimensions, "sha256": digest(texture)}
        report["limits"].append("A returned texture still needs visual and positive-control checks.")
    write_json(directory / "probe.json", report)
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="New or empty isolated experiment directory")
    parser.add_argument("--case", required=True, choices=CASES)
    parser.add_argument("--lab-source")
    args = parser.parse_args()
    capture(args.root, args.case, args.lab_source)


if __name__ == "__main__":
    main()
