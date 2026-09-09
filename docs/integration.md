# Enfusion integration

The installed Workbench can validate isolated addons and export a rendered viewport. That is a useful research interface. It does not expose a verified path for inserting this network into live gameplay.

| Capability | State |
| --- | --- |
| Stable game and Workbench discovery | Verified by Enfusion Lab doctor |
| Isolated addon compilation | Verified in this milestone |
| Explicit camera and full-size scene export | Verified in this milestone |
| Native GPU processing of exported image | Implemented by this repository |
| Full lighting graph on prepared scene features | [Verified standalone](lighting-gpu.md); engine features unverified |
| Original camera color lookup | Visible native response; exact color mapping unverified |
| Pre-HUD linear/HDR scene color | Unverified |
| Native scene-resource handles and fences | Unverified |
| Depth, normals, motion and material textures | Unverified |
| Correct scene-stage output composition | Unverified |
| Packaged runtime mod or multiplayer support | Unverified |

These states describe the inspected interface and local evidence. They are not claims that the engine lacks these buffers internally.

The [technical feasibility review](feasibility.md) adds installed-SDK declarations for material/resource workflows, render-target scaling and camera post-processing. None establishes arbitrary neural dispatch and composition. The [lighting model](lighting-study.md) consumes original Cycles surface passes. Its [native GPU graph](lighting-gpu.md) is verified independently, while those inputs remain unavailable as verified Enfusion exports.

## Bridge experiment

Find an authoritative supported extension interface and a minimal sample. Demonstrate an identity pass at the intended scene stage, then an invert control with exact pixel validation. Record resource formats, color conventions, frame identity, queue ownership, synchronization and output placement relative to HUD, scopes and tone mapping.

If an external Windows capture viewer is used as an intermediate experiment, report capture age, extra latency, copies and missing scene buffers. A post-composited screenshot processor cannot silently inherit guarantees about HUD protection or engine integration.

The same separation applies to other Enfusion games. A shared neural core does not imply access to every game's renderer or asset data. Build and validate each adapter independently.

## Feature and execution requirements

The verified GPU graph expects 20 ordered values per pixel. The mapping below follows `enr/lighting.py` and the frozen model, rather than assuming any image or similarly named engine property is interchangeable with a training input.

| Input | Required meaning | Current Enfusion evidence |
| --- | --- | --- |
| Source RGB, 3 values | Nonnegative scene-linear radiance, transformed with `log1p` | RGB8 screenshot export works; a matching linear/exposure convention is unverified |
| Position, 3 values | Visible surface position in the original scene coordinate convention, divided by four | Entity and camera positions are available; per-pixel visible surface positions are unverified |
| Normal, 3 values | Surface shading normal in the same coordinate convention | Collision traces report polygon normals; equality with rendered shading normals is unverified |
| Material, 5 values | Surface albedo RGB, roughness and metallic value evaluated at the pixel | Material resources and selected parameters are available; evaluated surface buffers are unverified |
| View, 3 values | Normalized surface-to-camera direction | Camera controls work; reconstruction also requires the missing surface positions |
| Light offset, 3 values | The controlled light position minus surface position, divided by four | A light can be placed; equivalence to the training light and mapping of sun, environment or multiple lights are unverified |

Source alpha and a validity flag are additional transport fields. Invalid pixels must retain source RGB, and alpha must survive exactly. Coordinate origin, axis orientation, units, normal transforms and exposure must be verified together; feeding native world coordinates directly into the frozen graph is not an established mapping. The model's single light-position input also does not describe arbitrary game illumination by itself.

`TraceParam` is explicitly a collision-query structure. Its polygon normal, collider and surface-material fields do not establish a rendered G-buffer, texture sampling, normal maps or alpha-tested visibility. They must not silently replace the surface inputs above. [Collision trace API](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/interfaceTraceParam.html)

The execution proof additionally needs an identified resource format and owner, a defined rendering stage, frame identity and synchronization, an independently checked passthrough/change/bypass sequence, and execution of the actual scene-conditioned graph. A camera frame counter alone is not a GPU completion fence. After this contract works, measure the whole frame and test aligned actual-Arma references and motion across the required environments. Standalone GPU agreement cannot establish any of these engine properties.

## Interface audit

The follow-up audit reads both installed generated SDKs, including full interface HTML for static methods omitted from JavaScript member indexes. The retained first index-only scan is therefore a discovery pass, not a complete member inventory. Even the expanded keyword scan cannot prove that differently named, undocumented or private interfaces are absent; method signatures and behavior remain the deciding evidence.

The completed scan covers 8,984 full interface pages and 73,747 own-member rows. Its two custom-GPU keyword matches are unrelated log-buffer and spline-point methods. Known static-method controls are present. One source page contains an invalid UTF-8 byte; the initial decoding failure is retained and the completed scan preserves the source bytes while validating extracted names. The [review record](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-renderer-interface-v1.json) binds source hashes, exact search expressions, both earlier attempts and the feature contract. Run `scripts/audit_enfusion_interfaces.py --sdk-root <Workbench/docs> --out <new-directory>` to reproduce the inventory. It reads documentation and launches no engine process.

The reviewed material API constructs or loads an existing material class and changes its parameters. The post-process enum names built-in effect classes. Neither reviewed declaration identifies a custom shader compilation or dispatch entry point. The Resource Manager options list a “Generate Shaders” setting, but the page provides no custom shader source format or extension example for it. [Material API](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/interfaceMaterial.html) · [Effect types](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/group__World.html) · [Resource Manager options](https://community.bistudio.com/wiki/Arma_Reforger:Resource_Manager:_Options)

`RTTextureWidget` binds a widget render resource to an entity material through `$rendertarget` or `$renderview`. `RenderTargetWidget` selects a world/camera and controls refresh, size and format. These declarations describe engine-managed views; they do not provide a native texture handle, queue or external model-output import in the reviewed signatures. `TextureResourceInfo` describes source-texture conversion metadata. Its name is not evidence of a live GPU resource interface. [RTTextureWidget](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/interfaceRTTextureWidget.html) · [RenderTargetWidget](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/interfaceRenderTargetWidget.html) · [TextureResourceInfo](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/interfaceTextureResourceInfo.html)

The integration requirements remain unmet. A specific supported interface and minimal sample are needed before another full-model engine attempt. Continue the separately scoped color-lookup study only for questions it can resolve; a pointwise color transform cannot supply the missing surface inputs. More training or repetitions of the failed screenshot/widget routes cannot close this contract.

## Color lookup control

The [completed static control](color-lookup.md) uses the documented camera post-processing path. `SetCameraPostProcessEffect` accepts a material, and the public effect types include `ColorGrading`. Native schema inspection, original volume import and visible inversion/constant-color responses now work. This is a limited color effect, with no arbitrary neural dispatch or scene-buffer access. [BaseWorld API](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/interfaceBaseWorld.html) · [Effect types](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/group__World.html)

Workbench documents `VolumeTexture` conversion from 256 × 16 to 16 × 16 × 16. All three original compiled volumes match their source lattice exactly. The engine rejects priority 1000 and accepts the separately declared priority-19 requests. The constant lookup stores [51, 102, 204] but exports [123, 169, 231] everywhere; direct display-code mapping fails. Stored axis order is verified, while shader sampling, transfer, strength and placement relative to exposure/tone mapping remain open. Removal before settling restores normal appearance but has no exact or motion proof. [Texture import](https://community.bistudio.com/wiki/Arma_Reforger:Textures#VolumeTexture)

A pointwise RGB model can in principle be approximated by a finite color lookup table. That is an inference about a possible implementation; no trained transform has been tested here. The current RGB-only model fails aggregate synthetic fidelity checks. The working effect does not make that model suitable or provide the scene inputs required by the full model. It does not reconstruct missing spatial detail or implement arbitrary neural dispatch.

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
