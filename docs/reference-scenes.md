# Reference scenes

The first pack defines three static camera/lighting probes in the installed Arland world. Each scene is captured three times in separate Workbench simulations. It tests whether the same requested scene produces comparable images.

This page retains the v1 baseline. The newer [capture controls](capture-controls.md) add projection and exposure checks, explicit settings files and a recorded camera path. The separate [material room](material-room.md) supplies original synthetic reference data.

| Scene | View | Time | Group |
| --- | --- | --- | --- |
| `forest-east-noon` | East from [2048,60,2048] | 13:00 | arland-center |
| `forest-north-noon` | North from [2048,60,2048] | 13:00 | arland-center |
| `forest-east-evening` | East from [2048,60,2048] | 18:30 | arland-center |

All three use 21 June 1989, the `Clear` weather state, a requested wind speed of zero, and eight simulation seconds before export. Coordinates are in metres, with Y as height. Directions are unit look vectors. The shared world and nearby viewpoints make these related observations, so the entire group is assigned to **diagnostic** use.

The pack contains original camera/configuration definitions, not original terrain or game assets. Arland remains a base-game dependency. A material chart, dedicated geometry fixtures and animated sequences are not included in this version.

[View all three scenes](comparisons.md#reference-views). The gallery shows the first unprocessed capture from each variant, with full-resolution PNG links.

## First measured batch

Nine full-size captures completed on 8 September 2026 at 1839 × 947. Each of the three scene variants was visually inspected. Camera and environment telemetry matched the requested controls in all nine runs. Every pair's estimated global integer translation was [0,0], but the images were not pixel-identical.

| Scene | RGB MAE range | RGB RMSE range | Changed pixels |
| --- | --- | --- | --- |
| East, noon | 0.818–1.425 | 3.454–5.006 | 34.2–42.5% |
| North, noon | 0.314–0.833 | 1.688–4.169 | 20.4–30.8% |
| East, evening | 0.408–2.341 | 2.072–7.527 | 24.8–45.4% |

Errors are in 8-bit RGB code values. Changed pixels have at least one unequal RGB channel; even a one-code-value difference counts. Each range covers all three pairs within a scene. Alpha matched exactly in every pair.

This establishes repeated camera/environment conditions, not deterministic pixels. Foliage animation, streaming and temporal rendering may contribute to the differences; their individual contributions have not been isolated. The simulation frame count also varied between runs despite the fixed settle duration. The result is a baseline for measuring those effects.

[Complete numerical report](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/reference-scenes-v1.json). The full capture collection and machine logs remain in the local experiment directory; selected screenshots are published in the gallery with attribution and hashes. The first compile attempt failed on an unsupported world cast; that failed run was retained, and the corrected adapter passed compilation before the measured captures.

## Capture

The batch command uses Enfusion Lab's existing process ownership, addon snapshots, compilation checks and PNG verification. It does not modify the installed plugin or Steam files. Install Enfusion Lab separately or specify its source directory.

```powershell
python -m enr.references capture --root experiments/local/reference-run-01 --lab-source path/to/enfusion-lab
```

Use a new root for each batch. The command initializes one isolated project per scene, copies the project-owned capture adapter, validates it, and captures the required repeats sequentially. It records an incrementally updated `batch.json`. Failed runs and logs remain in the batch directory.

To use Enfusion Lab MCP tools directly, initialize a dedicated project, then prepare its scene configuration:

```powershell
python -m enr.references prepare --scene forest-east-noon --project experiments/local/reference-v1/forest-east-noon
```

Run the plugin's `validate` and `capture` tools with that project, the pack's world/camera, an eight-second settle and a bounded timeout. The shared batch CLI is the simpler route for repeat collections.

## Controls and observations

The adapter applies date, time of day, weather state and wind overrides through documented engine APIs. It records their observed values immediately before requesting the screenshot. The analysis rejects a run if camera or environment telemetry disagrees with the requested scene.

Time of day is reapplied each update. Weather is placed in the requested looping state. Wind override does not establish that every foliage animation has stopped. Simulation frame number and elapsed time are recorded; frame scheduling and procedural animation phase are not fixed.

Output dimensions are read from the actual PNG and must match between repeats. Render scale, FSR, quality preset, field of view and temporal jitter remain unverified in this version. They are represented as null in the manifest. An isolated default profile is not a pinned rendering configuration.

The reported HDR brightness and scene-middle-brightness values are observations. Their presence does not establish a linear/HDR pixel contract or fixed exposure.

## Analyze repeats

```powershell
python -m enr.references analyze --batch experiments/local/reference-run-01/batch.json --out experiments/local/reference-run-01/reanalysis.json
```

Analysis verifies pack and image hashes, addon consistency, camera/environment telemetry, dimensions and the expected number of distinct captures. It compares every pair of repeats, retaining RGB MAE/RMSE, PSNR, changed-pixel fraction, channel drift and exact alpha equality.

An integer translation estimate searches a ±3-pixel window using image gradients on a fixed interior region. It samples every fourth pixel for alignment. The sign convention is: reference(x,y) corresponds to repeat(x+dx,y+dy). This is an image-derived estimate, not engine motion vectors or proof that every object aligns. A result at the search boundary needs further investigation; a flat image has no reliable alignment estimate.

The unaligned pixel metrics are always retained. Images are not warped or color-matched before the reported differences are computed.

## Data use

Repeated game renders are not aligned photorealistic ground truth. These scenes can characterize capture variability and processing stability. They must not be used as supervised appearance targets without a separate target-generation method.

Before constructing train/validation/test datasets, define non-overlapping scene groups with asset and location provenance. The pack validator rejects a group that spans multiple splits. Variants of the same location stay together.

For appearance targets, the next experiment is an original controlled scene containing known geometry and measured material parameters, rendered through an authorized reference renderer with matching camera and lighting. Geometry, materials, color transfer, tone mapping and pixel alignment need separate checks before the outputs form a valid pair.
