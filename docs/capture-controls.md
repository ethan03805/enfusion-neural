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

Workbench's game workspace reports 128 × 128 while the screenshot comes from a 2560 × 1440 viewport. Changing the game workspace's resolution scale, or loading a startup scale of 0.25, changes stored values without establishing a corresponding change in the exported viewport. These values cannot prove the viewport's internal resolution or FSR state.

The adapter uses `-forceSettings`, `-cfg` and `-diagMenu` with files inside each isolated run. Saved user editor preferences are excluded. This improves reproducibility, but it does not close the viewport verification gap. See Bohemia's [startup parameter documentation](https://community.bistudio.com/wiki/Arma_Reforger:Startup_Parameters) and [diagnostic menu documentation](https://community.bistudio.com/wiki/Arma_Reforger:Diag_Menu).

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
