"""Launch an isolated Reforger session. No game-installation writes or input injection."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
SCENES = {
    "town": ([4773.46, 166.042, 7094.57], 0, 13),
    "town-evening": ([4773.46, 166.042, 7094.57], 0, 18.5),
    "foliage": ([4508.76, 15.8, 10764], 0, 13),
}


def set_field(text, module, key, value):
    """Modify a single existing module, respecting nested config braces."""
    # A saved module has an instance name followed by its class and optional GUID.
    match = re.search(r'(?m)^\s*\w+\s+' + re.escape(module) + r'[^\n]*\{\s*$', text)
    if not match:
        raise ValueError("Missing settings module " + module)
    start = match.end(); depth = 1; end = start
    quoted = False
    while end < len(text) and depth:
        c = text[end]
        if c == '"': quoted = not quoted
        if not quoted:
            if c == '{': depth += 1
            if c == '}': depth -= 1
        end += 1
    if depth: raise ValueError("Unclosed settings module")
    body = text[start:end-1]
    pattern = r"(?m)^\s*" + re.escape(key) + r"\s+[^\n]*"
    if re.search(pattern, body): body = re.sub(pattern, "\n  " + key + " " + str(value), body, count=1)
    else: body = "\n  " + key + " " + str(value) + body
    return text[:start] + body + text[end-1:]


def prepare(out, scene, preset, automatic, settings_source):
    out.mkdir(parents=True, exist_ok=False)
    addon = out / "addon"
    shutil.copytree(ROOT / "adapters/playable", addon)
    position, yaw, hour = SCENES[scene]
    config = "class ENR_PlayableConfig {\n static vector Position = \"%s\";\n static float Yaw = %s;\n static float Hour = %s;\n static bool Automatic = %s;\n}\n" % (" ".join(map(str, position)), yaw, hour, str(automatic).lower())
    (addon / "Scripts/Game/ENR_PlayableConfig.c").write_text(config, encoding="utf-8")
    settings = settings_source.read_text(encoding="utf-8-sig")
    changes = {"VideoUserSettings": {"WindowMode": "BORDERLESS", "ScreenWidth": 2560, "ScreenHeight": 1440, "ResolutionScale": 1, "FsrEnabled": 0, "Vsync": 0, "MaxFps": 120, "DistantShadowsQuality": "HIGH"}, "PipelineUserSettings": {"ShadowQuality": "High"}}
    if preset in ("scale", "combined"):
        changes["VideoUserSettings"].update(ResolutionScale=.75, FsrEnabled=1)
    if preset in ("shadows", "combined"):
        changes["PipelineUserSettings"]["ShadowQuality"] = "Medium"
        changes["VideoUserSettings"]["DistantShadowsQuality"] = "LOW"
    if preset in ("effects", "combined"):
        changes["PPEffectsSettings"] = {"SSDO": 0, "SSR": 0}
    for module, fields in changes.items():
        for key, value in fields.items(): settings = set_field(settings, module, key, value)
    # -profile selects a root; the engine mounts its nested profile/ as $profile:.
    settings_path = out / "profile/profile/.save" / settings_source.parents[1].name / "settings/ReforgerEngineSettings.conf"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(settings, encoding="utf-8")
    return addon, {"scene": scene, "preset": preset, "automatic": automatic, "requested_settings": changes, "settings_sha256": hashlib.sha256(settings_path.read_bytes()).hexdigest(), "addon_hashes": {str(p.relative_to(addon)): hashlib.sha256(p.read_bytes()).hexdigest() for p in addon.rglob('*') if p.is_file()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--game", type=Path, default=Path("C:/Program Files (x86)/Steam/steamapps/common/Arma Reforger/ArmaReforgerSteam.exe"))
    parser.add_argument("--scene", choices=SCENES, default="town")
    parser.add_argument("--preset", choices=("standard", "scale", "shadows", "effects", "combined"), default="standard")
    parser.add_argument("--automatic", action="store_true", help="20 s scripted walking, 10 s heading sweep, starting at simulation second 30")
    parser.add_argument("--settings-source", type=Path)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if not args.settings_source:
        home = Path(os.environ["USERPROFILE"])
        matches = [p for folder in (home/'OneDrive/Documents', home/'Documents') for p in (folder/'My Games/ArmaReforger/profile/.save').glob('*/settings/ReforgerEngineSettings.conf')]
        if not matches: parser.error("Pass --settings-source pointing to your saved ReforgerEngineSettings.conf")
        args.settings_source = matches[0]
    out = args.out.resolve()
    addon, report = prepare(out, args.scene, args.preset, args.automatic, args.settings_source)
    report["created_unix_s"] = time.time()
    report["argv"] = [str(args.game), "-profile", str(out/'profile'), "-gproj", str(addon/'addon.gproj'), "-addonsDir", str(args.game.parent/'addons'), "-world", "worlds/GameMaster/GM_Eden.ent", "-play", "-nosplash", "-maxFPS", "120"]
    if not args.prepare_only:
        process = subprocess.Popen(report["argv"], cwd=args.game.parent)
        report["pid"] = process.pid
        print(f"Started local Reforger PID {process.pid}; session retained in {out}")
    (out/'launch.json').write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__": main()
