# Enfusion integration

The installed Workbench can validate isolated addons and export a rendered viewport. That is a useful research interface. It does not expose a verified path for inserting this network into live gameplay.

| Capability | State |
| --- | --- |
| Stable game and Workbench discovery | Verified by Enfusion Lab doctor |
| Isolated addon compilation | Verified in this milestone |
| Explicit camera and full-size scene export | Verified in this milestone |
| Native GPU processing of exported image | Implemented by this repository |
| Pre-HUD linear/HDR scene color | Unverified |
| Native scene-resource handles and fences | Unverified |
| Depth, normals, motion and material textures | Unverified |
| Correct scene-stage output composition | Unverified |
| Packaged runtime mod or multiplayer support | Unverified |

These states describe the inspected interface and local evidence. They are not claims that the engine lacks these buffers internally.

The [technical feasibility review](feasibility.md) adds installed-SDK declarations for material/resource workflows, render-target scaling and camera post-processing. None establishes arbitrary neural dispatch and composition. The [lighting model](lighting-study.md) currently consumes original Cycles surface passes; its inputs are not verified Enfusion exports.

## Bridge experiment

Find an authoritative supported extension interface and a minimal sample. Demonstrate an identity pass at the intended scene stage, then an invert control with exact pixel validation. Record resource formats, color conventions, frame identity, queue ownership, synchronization and output placement relative to HUD, scopes and tone mapping.

If an external Windows capture viewer is used as an intermediate experiment, report capture age, extra latency, copies and missing scene buffers. A post-composited screenshot processor cannot silently inherit guarantees about HUD protection or engine integration.

The same separation applies to other Enfusion games. A shared neural core does not imply access to every game's renderer or asset data. Build and validate each adapter independently.

## Screenshot return probe

The image-return and optional vehicle/character scripts compiled successfully in Workbench's silent ScriptEditor mode. No world or capture was launched by that validation. [Compilation evidence](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-image-bridge-compile-v1.json) binds the actual addon snapshot and log. Runtime execution remains pending.

The prototype requests a screenshot texture and copies it into an image widget. Separate controls export RGBA8, run identity, inversion or the original bootstrap model on the external CPU, then attempt to load the output into the widget. These routes use the documented [System screenshot interfaces](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/interfaceSystem.html) and [ImageWidget interfaces](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/interfaceImageWidget.html). Successful declarations and compilation do not establish that the requested format or presentation route works.

`enr/image_bridge.py` checks the actual run snapshots, camera/environment telemetry, worker output, uploaded texture and displayed pixels separately. Its exact-return check fails if even one channel differs. A successful outer screenshot capture cannot override a failed widget operation. `System.GetTickCount` records elapsed milliseconds across the request and final readback save, including deliberate settling and file operations; this is neither a display fence nor sustained frame rate. Scene buffers, HUD/scopes and live neural lighting remain separate unverified fields even if the image return is exact.

```powershell
python scripts/probe_enfusion_image_bridge.py --mode copy --validate-only --out experiments/local/bridge-compile-01 --lab-source <enfusion-lab-root>
python scripts/probe_enfusion_image_bridge.py --mode copy --out experiments/local/bridge-copy-01 --lab-source <enfusion-lab-root>
python scripts/summarize_enfusion_image_bridge.py --root experiments/local/bridge-copy-01 --out experiments/local/bridge-copy-01/analysis.json
```

Run scene/capture experiments serially with other GPU experiments. Use a new output directory per attempt; preserve failures. Inspect actual images before publishing them as environment coverage. For additional worlds, the probe requires `--world-inventory` pointing to a completed native resource inventory that observed the exact requested world. This establishes the resource name, not successful loading or useful framing. The default sequence adapter retains its established Arland restriction.
