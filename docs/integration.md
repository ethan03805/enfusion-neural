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

## Color lookup control

The next proposed control uses the documented camera post-processing path. `SetCameraPostProcessEffect` accepts a material, and the public effect types include `ColorGrading`. These declarations establish a lead, not a working custom effect. [BaseWorld API](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/interfaceBaseWorld.html) · [Effect types](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/group__World.html)

Workbench also documents `VolumeTexture` conversion from a flat image, for example 256 × 16, to a 16 × 16 × 16 lookup texture. Its use by an original color-grading material remains to be verified. First inspect the material schema and native resource names read-only; then declare original identity and known-color controls before capturing. Verify axis order, sampling, color encoding, strength, effect removal and placement relative to exposure and tone mapping. Keep every failed control. [Texture import](https://community.bistudio.com/wiki/Arma_Reforger:Textures#VolumeTexture)

A pointwise RGB model can in principle be approximated by a finite color lookup table. That is an inference about a possible implementation, not proof that the engine accepts it. The current RGB-only model fails aggregate synthetic fidelity checks. A successful lookup control would neither make that model suitable nor provide the scene inputs required by the full model. It would not reconstruct missing spatial detail or implement arbitrary neural dispatch.

Acceptance for this bounded experiment: native material/texture validation, repeated unchanged-image and known-transform controls measured against an independent CPU lookup reference, and verified effect removal. Declare numerical limits after characterizing repeat noise and lookup quantization, before evaluating the reserved controls. Exact-return checks elsewhere remain unchanged. Test movement, exposure changes, camera cuts and a second resolution only after the static control works. HUD/scopes and scene-stage composition remain explicit unknowns until observed.

## Screenshot return probe

The image-return and optional vehicle/character scripts compiled successfully in Workbench's silent ScriptEditor mode. No world or capture was launched by that validation. [Compilation evidence](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-image-bridge-compile-v1.json) binds the actual addon snapshot and log. Three texture-copy runs then failed: two timed out and the third crashed. The [runtime evidence](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-image-bridge-v1.json) retains each actual script, native outcome and verification result.

| Texture-copy attempt | Last observed operation | Outcome |
| --- | --- | --- |
| Immediate readback | Screenshot copied into widget | 240-second timeout |
| Readback on a later update | Widget raw-data request | 240-second timeout |
| Display before readback | Widget visible and workspace updated | Native crash before readback |

Copy acceptance is not evidence that the texture can be displayed or read back. All five integration verification fields remain false for these attempts. Native dumps and raw machine logs remain local.

The separate identity/file-return control also timed out. It requested `MakeScreenshotRawData` but never received the source callback, so no PNG reached the external worker and no upload was attempted. This fourth failure is retained in the same runtime evidence. A further file-based probe would need to use the ordinary screenshot export already verified by the capture adapter; repeating the raw-data request has no supporting result.

The prototype requests a screenshot texture and copies it into an image widget. Separate controls export RGBA8, run identity, inversion or the original bootstrap model on the external CPU, then attempt to load the output into the widget. These routes use the documented [System screenshot interfaces](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/interfaceSystem.html) and [ImageWidget interfaces](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/interfaceImageWidget.html). Successful declarations and compilation do not establish that the requested format or presentation route works.

`enr/image_bridge.py` checks the actual run snapshots, camera/environment telemetry, worker output, uploaded texture and displayed pixels separately. Its exact-return check fails if even one channel differs. A successful outer screenshot capture cannot override a failed widget operation. `System.GetTickCount` records elapsed milliseconds across the request and final readback save, including deliberate settling and file operations; this is neither a display fence nor sustained frame rate. Scene buffers, HUD/scopes and live neural lighting remain separate unverified fields even if the image return is exact.

```powershell
python scripts/probe_enfusion_image_bridge.py --mode copy --validate-only --out experiments/local/bridge-compile-01 --lab-source <enfusion-lab-root>
python scripts/probe_enfusion_image_bridge.py --mode copy --out experiments/local/bridge-copy-01 --lab-source <enfusion-lab-root>
python scripts/summarize_enfusion_image_bridge.py --root experiments/local/bridge-copy-01 --out experiments/local/bridge-copy-01/analysis.json
```

Run scene/capture experiments serially with other GPU experiments. Use a new output directory per attempt; preserve failures. Inspect actual images before publishing them as environment coverage. For additional worlds, the probe requires `--world-inventory` pointing to a completed native resource inventory that observed the exact requested world. This establishes the resource name, not successful loading or useful framing. The default sequence adapter retains its established Arland restriction.

## Ordinary file export

The ordinary screenshot function succeeds where the raw-data callback did not. It exports RGB8. The first worker rejected those channels; the revised file route preserves RGB exactly and supplies an explicitly recorded opaque alpha channel. Source alpha is unavailable.

Both identity and inversion then complete the external CPU operation and load a 2560 × 1440 PNG into the widget. `GetTextureRawData` returns false for both. The final ordinary screenshot remains the rendered scene: mean RGB difference from worker output is 5.01 code values for identity and 129.20 for inversion. The [file-return evidence](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-file-return-v1.json) retains all three attempts, independent CPU checks and final-capture differences. Every bridge verification field remains false.

This establishes file export, CPU processing and an accepted widget load. It does not establish that the processed image reaches the viewport or display. Further work needs an authoritative presentation route and scene-buffer contract, rather than another identical callback retry.

```powershell
python scripts/probe_enfusion_image_bridge.py --mode invert --source-interface file --out experiments/local/file-return-recheck --lab-source <enfusion-lab-root>
```

## Inventory without a world

Normal ScriptEditor initialization now runs a search-only inventory without loading a world. It found eight `.ent` resources, including `{853E92315D1D9EFE}worlds/Eden/Eden.ent`, and exited naturally with code 0 after the completion callback. [Native inventory evidence](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-world-inventory-v1.json) records script and log hashes. A subsequent WorldEditor run loaded Everon and exported a verified 2560 × 1440 overview. Its distant coast-and-sky view does not establish city or interior coverage. The [Everon scout evidence](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-everon-scout-v1.json) also retains an earlier timeout during material traversal.

The [Workbench plugin documentation](https://community.bistudio.com/wiki/Arma_Reforger:Workbench_Plugin) describes command-line callbacks. The probe uses Lab discovery, isolated initialization and compilation, followed by a separate bounded inventory operation. It requests an initially hidden module window and preserves private settings. Its completion check requires natural exit, exactly one callback completion and each requested search result; exit code 0 alone is insufficient.

```powershell
python scripts/probe_enfusion_resource_inventory.py --out experiments/local/world-inventory-01 --lab-source <enfusion-lab-root> --startup module --extension ent --query Eden --query Everon
```

The additional-world loader accepts this distinct inventory operation without pretending an image was captured. It binds the native manifests, log, scripts and completion records. Keep the resulting `resources.json` with its raw run directories and pass it as `--world-inventory` to a scene probe.

Three earlier attempts remain visible. Two silent startups compiled and exited without invoking the callback; adding `-run` did not resolve them. A normal startup invoked the full callback but timed out before returning any inventory records. The successful version calls only the resource searches, omitting the earlier material-file traversal. [Silent-attempt evidence](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-resource-inventory-silent-v1.json) and the native inventory report retain these failures. Other modules were not tested. None of these runs proves a neural rendering bridge.

The revised WorldEditor location query reports all 170 named locations among 650 map descriptors, including Saint-Philippe and Montignac. [Named-location evidence](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-everon-locations-v1.json) binds the completed capture and compiled script. `scripts/capture_enfusion_scout.py` accepts a camera config and the native world inventory, verifies the exported sequence, and records optional vehicle/character placement. Its output is source-only; each scene needs visual review before it counts as environment coverage.

The first [Saint-Philippe source scene](arma-scenes.md) now has inspected buildings, foliage, fences, an upright M998 and a standing rifleman. Two failed placement attempts remain recorded. Source capture does not establish a matching lighting target or model behavior on those assets.
