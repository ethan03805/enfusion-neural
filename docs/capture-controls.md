# Capture controls

The motion capture adapter fixes the camera, projection, exposure and environment, and starts Workbench with separate editor, engine and diagnostic settings files. It verifies settings readback and image dimensions. Internal viewport resolution and FSR remain unverified.

| Control | Requested value | Verification |
| --- | --- | --- |
| Export | 2560 × 1440, full-screen viewport | Every PNG and viewport report |
| Projection | 60° vertical FOV | Projected horizontal and vertical calibration points |
| Clip distances | 0.1–2000 m | Far-plane readback; near plane requested |
| Exposure | HDR brightness 0.00456415 | Every sample; engine units |
| Environment | 21 June 1989, 13:00, Clear, zero wind | Final telemetry; reapplied during capture |
| Quality | Versioned `ENR_Engine.conf` | Selected engine module values checked |
| Render scale / FSR | 1.0 / disabled | Engine settings readback only; viewport effect unverified |

The quality file declares medium shadows, high environment quality, no MSAA or alpha-to-coverage, and PPAA value 2. The complete observed fields are retained in the [control report](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/capture-controls-v1.json). Numeric engine enums are tied to the recorded Tools build, not assumed portable to later versions.

## Viewport limitation

Workbench's game workspace initially reports 128 × 128, then reaches 2560 × 1440 after the full-screen viewport settles. `System.GetRenderingResolution` still reports 128 × 128. Applying workspace scale 0.25 and disabling FSR repeatedly after startup changes their readback without establishing a corresponding change in the exported scene. These values cannot prove the viewport's internal resolution or FSR state.

The adapter uses `-forceSettings`, `-cfg` and `-diagMenu` with files inside each isolated run. Saved user editor preferences are excluded. This improves reproducibility, but it does not close the viewport verification gap. See Bohemia's [startup parameter documentation](https://community.bistudio.com/wiki/Arma_Reforger:Startup_Parameters) and [diagnostic menu documentation](https://community.bistudio.com/wiki/Arma_Reforger:Diag_Menu).

## Diagnostic investigation

The manual F1 save succeeded. Its 59-byte file contains four diagnostic entries, with no explicit render-scale or FSR value. Missing entries do not establish their state. A separate `Render world` override produces an all-black, full-size screenshot, confirming that Workbench loads the isolated diagnostic file. That control fails the normal exposure check and is excluded from accepted scene captures.

Named 50% resolution presets with FSR enabled and disabled did not establish a corresponding change in the main viewport. The SDK workspace control also failed this check after startup. Image-detail measurements stayed close to the baseline; those measurements alone cannot identify the actual internal resolution.

A separate render-target probe reaches 2560 × 1440 and reads back explicit scale and FSR values. However, `ImageWidget.GetTextureRawData` returns false and produces no exported texture. This does not establish a usable offscreen capture path. Bohemia documents the controls in [RTTextureWidget](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/interfaceRTTextureWidget.html) and the callback in [ImageWidget](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/interfaceImageWidget.html); their availability does not prove that this adapter can use them successfully.

The [probe report](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/viewport-probes-v1.json) retains the saved values, tested presets, run and source hashes, all fourteen investigation runs, image measurements and rejected exports. It includes the early widget-sizing attempts and a compile failure. No existing screenshot or video has been relabeled as fully pinned.

To reproduce the settled workspace probe:

```powershell
python scripts/probe_viewport.py --case workspace-quarter --root experiments/local/viewport-check --lab-source path/to/enfusion-lab
```

Other cases are `diag-render-off`, `diag-half-off`, `diag-half-on` and `texture-export`. Each requires a new directory and runs an isolated compile/capture through Enfusion Lab. Run them serially. `probe.json` distinguishes capture completion from the sequence checks and texture-export result; process success does not certify viewport settings. These cases are diagnostic experiments, not training captures.

## Static variation

The final preset was captured three times in separate processes. Every pair had estimated integer translation [0,0] and identical alpha. RGB MAE ranged from **0.379 to 0.891**, with RMSE from **2.032 to 3.585** in 8-bit code values. These are all three pairs, without image registration or color correction.

| Selected region | RGB MAE range |
| --- | --- |
| Sky | 0–0.000002 |
| Foliage | 0.538–1.275 |
| Ground and grass | 0.066–0.157 |

The report specifies each rectangle in source pixels. This spatial pattern suggests scene animation or temporal rendering contributes to the differences; it does not distinguish foliage phase, stochastic rendering, streaming or other causes.

An earlier three-run probe ranged from 1.416 to 2.358 RGB MAE. It is retained in the same report. That probe used an unrecognized alpha-to-coverage enum string, which read back as zero. The final preset states `NONE` explicitly and checks the value. Both batches observed zero, so the lower variation in the final batch is not evidence that this spelling correction improved rendering.

## Camera path

`scenes/arland-motion-v1.json` defines 80 samples from [2048,60,2048] to [2050,60,2048], with yaw moving from 90° to 98°. The camera is held for six simulation updates per sample. Export starts after eight simulation seconds; a final still at the start camera acts as the Enfusion Lab completion sentinel.

Each numbered sample records camera, projection, exposure, simulation time, world frame and image hash. Verification rejects missing or reordered telemetry, unexpected images, mismatched dimensions, camera drift and changed settings. The GPU presentation frame ID is unavailable; holding the camera before export reduces request/render ambiguity but is not a presentation fence.

```powershell
python -m enr.sequence --root experiments/local/static-01 --static --repetitions 3 --lab-source path/to/enfusion-lab
python -m enr.sequence --root experiments/local/motion-01 --lab-source path/to/enfusion-lab
```

Use new directories. Enfusion Lab remains responsible for the addon snapshot, process lock, compile validation, owned process termination and final still verification. The sequence module adds a CLI-local extension for the three settings flags; it must not run concurrently in the same Python process.

To process a completed sequence and encode its comparison:

```powershell
python -m enr.motion process --sequence path/to/run/sequence.json --out experiments/local/motion-output-01
python -m enr.motion video --sequence path/to/run/sequence.json --out experiments/local/motion-output-01
```

The first published sequence spans 21.762 simulation seconds between its first and last sample. Its **four-second, 20 FPS video is retimed playback**. Offline processing and CPU verification took 116.641 seconds for all 80 frames. Neither number is a playable frame-rate result. [Watch the comparison](comparisons.md#motion).
