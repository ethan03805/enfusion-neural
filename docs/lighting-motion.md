# Scene transfer and motion

The lighting model from the first room is evaluated unchanged on two camera/light paths. One path uses the original room as a control. The second uses a new arrangement of partitions, crates, contrasting bars and foreground posts. Both use the original material constants, so this tests geometry and layout transfer without introducing a new material library.

The plan and frozen model hashes were committed before rendering. No fitting, feature normalization, checkpoint selection or adjustment of model settings uses either sequence. This remains an offline synthetic experiment with original assets.

The frozen model lowers average image error in both rooms, but its advantage over simpler methods does not transfer to the new layout. **The RGB-only model performs better on the new room, and the scene-conditioned model makes marking contrast less accurate.** Small measured temporal differences do not establish a meaningful stability improvement.

## Synchronized comparisons

Each video shows the source, frozen model output and independently sampled reference together. Every panel retains its original 480 × 270 pixels; a label band sits above the images. Each clip has 32 frames at 20 FPS and lasts 1.6 seconds. The clips are encoded offline and do not measure renderer performance.

<figure class="motion-comparison">
<video controls playsinline preload="none" poster="media/lighting-motion-known-poster.png" width="1440" height="302" aria-label="Original room motion control: source, frozen lighting model and independent reference"><source src="media/lighting-motion-known.mp4" type="video/mp4"><a href="media/lighting-motion-known.mp4">Download original-room comparison</a></video>
<figcaption>Original room · unseen camera/light path</figcaption>
</figure>

<figure class="motion-comparison">
<video controls playsinline preload="none" poster="media/lighting-motion-new-poster.png" width="1440" height="302" aria-label="New partition room: source, frozen lighting model and independent reference"><source src="media/lighting-motion-new.mp4" type="video/mp4"><a href="media/lighting-motion-new.mp4">Download new-room comparison</a></video>
<figcaption>New room · held-out geometry and layout</figcaption>
</figure>

Frame 16 from each path was selected for the posters and still images before inference. Video uses H.264, CRF 16 and 4:2:0 chroma; compression changes pixels. No frames are scaled, interpolated, dropped or retimed. Use the PNGs to inspect exact display pixels.

[Original-room source](media/lighting-motion-known-source.png) · [Model](media/lighting-motion-known-output.png) · [Reference](media/lighting-motion-known-reference.png)

[New-room source](media/lighting-motion-new-source.png) · [Model](media/lighting-motion-new-output.png) · [Reference](media/lighting-motion-new-reference.png)

## Results

Mean absolute RGB error against the independent reference, in 8-bit display code values, averaged over all 32 frames. Lower is better.

| Sequence | Source | Affine correction | RGB-only model | Scene-conditioned model |
| --- | ---: | ---: | ---: | ---: |
| Original room | 2.670 | 1.308 | 1.298 | **0.881** |
| New partition room | 2.954 | 2.757 | **1.520** | 2.335 |

The scene-conditioned model improves whole-image log-radiance error in all 64 frames. On the new room, both RGB-only and affine methods beat it in log-radiance RMSE; their ranking differs under display MAE, as shown above. The full report preserves both metrics. This is one held-out geometric layout using familiar material constants, not broad new-asset generalization.

Mean temporal reconstruction-error RMSE follows. These are changes in error on matched surfaces, not frame-to-frame image differences or frame times.

| Sequence | Source | Affine | RGB-only | Scene-conditioned | Reference seed difference |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original room | 0.007970 | 0.007943 | 0.008026 | 0.007953 | 0.008727 |
| New partition room | 0.007129 | 0.007109 | 0.007186 | 0.007120 | 0.008034 |

The mean temporal error is slightly below identity in both paths, meeting that literal planned threshold. The change is only about 0.2% in the original room and 0.1% in the new room; the reference seed difference is larger. Five of 31 new-room transitions become worse. This is insufficient evidence of a meaningful temporal improvement. The independent reference-noise comparison is not a correction to subtract from model error.

Thin-post and boundary errors decrease in every frame for the scene-conditioned model. The new-room marking region also has lower average error, but **mean absolute marking-contrast error increases from 0.0195 to 0.0306** in log-luminance units. RGB-only contrast error is 0.0300; the affine baseline gives 0.0020. Preserving region-average colors does not establish preservation of contrast. The new-room model output also has visible color and shadow disagreement with the reference.

Here, the contrast diagnostic uses Rec. 709 luminance weights on `log1p` RGB, then subtracts the mean over the dark bars from the mean over their white board. It is not physical luminance or Michelson contrast.

Source/paired-reference depth and object IDs agree exactly in all 64 frames. Valid temporal coverage ranges from 88.4% to 92.6%. Display roundtrip error is at most one code value, and output alpha matches exactly. CPU scene-model execution has a median near 37 ms per 480 × 270 frame, excluding feature construction, analysis and I/O. No native GPU implementation or net engine-frame saving is demonstrated.

## What changes

Both paths move the camera and a single area light with cubic smoothstep interpolation. Geometry stays static. In every frame, source and paired reference share the sampling seed and differ only in diffuse-bounce depth, 1 versus 12. Maximum and glossy bounces stay at 12. Each render uses 1024 samples, unchanged exposure and the same display transform. A second, independently seeded 12-bounce render is the primary evaluation target for every frame. Seeds also change between frames.

The new room's markings are original geometric bars. They test contrast and small boundaries; they are not texture decals, text recognition or detailed game assets. There are no people, vegetation, animation or exposure transitions in this experiment.

## Temporal measurement

For each output, calculate its error against the independent reference in `log1p` scene-linear RGB. Project the current surface position into the previous camera, sample the previous error there, and measure the change in error. This accounts for legitimate appearance changes from the moving light and camera.

Correspondences require matching object IDs across all four previous bilinear samples, world-position agreement within 4 cm, a normal dot product above 0.98, and a valid screen position. Current object boundaries are excluded from this temporal measure. Spatial errors on boundaries, thin posts, markings and unmatched interior pixels are recorded separately. Unmatched pixels are not all proven disocclusions.

The report retains valid coverage for every frame pair, camera self-projection checks and the temporal difference between the two reference seeds. Sampling noise and interpolation affect these measurements. They are not a perceptual flicker score, and a low value does not establish gameplay visibility or temporal fidelity.

## Consequence for the next model

The results suggest dependence on the training layout; this experiment does not isolate which input or architectural choice causes it. Treat both paths as published regression data from now on. Add multiple original training layouts, reserve another untouched scene for evaluation, and compare models with and without absolute world position under a fixed training budget. Include a marking-contrast gate and higher-convergence temporal references. Keep the current weights unchanged as a control.

This experiment supports continuing controlled data/model research. It does not justify aggressive texture or geometry reduction, an all-Reforger asset training run, or a live renderer claim. The supported Enfusion bridge remains a separate unresolved gate.

## Reproduce

Use the repository Python environment with the `references` optional dependency, an installed Blender, and FFmpeg/ffprobe on `PATH` for video encoding. The renderer defaults to CPU; the existing HIP setup may select one exact device with `--device HIP --device-name`. Commands install or provision nothing.

```powershell
blender --background --factory-startup --python-exit-code 1 --python scripts/render_lighting_motion.py -- --out experiments/local/motion-study-01
python scripts/evaluate_lighting_motion.py --root experiments/local/motion-study-01 --out experiments/local/motion-evaluation-01
blender --background --factory-startup --python-exit-code 1 --python scripts/display_lighting_study.py -- --root experiments/local/motion-evaluation-01 --renders experiments/local/motion-study-01
python scripts/summarize_lighting_motion.py --root experiments/local/motion-evaluation-01 --renders experiments/local/motion-study-01 --out experiments/local/motion-report-01.json
python scripts/video_lighting_motion.py --root experiments/local/motion-evaluation-01 --report experiments/local/motion-report-01.json --out experiments/local/motion-video-01
```

Use new output directories. The renderer creates both scenes directly from versioned JSON, saves editable `.blend` files and retains all RGB/auxiliary EXR passes. The evaluator loads the committed scene-conditioned, RGB-only and affine models; it contains no training step. Display conversion checks source/reference roundtrip error and exact alpha before video encoding.

[Frozen plan](https://github.com/ethan03805/enfusion-neural/blob/main/scenes/lighting-motion-v1.json) · [Complete numerical evidence](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/lighting-motion-v1.json) · [Video provenance](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/lighting-motion-video-v1.json) · [Model contract](https://github.com/ethan03805/enfusion-neural/blob/main/models/LIGHTING_MODEL_CARD.md)
