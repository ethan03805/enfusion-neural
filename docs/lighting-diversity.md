# Scene diversity

Four original layouts now train the lighting model. A separate loading bay selects checkpoints; a cross-courtyard is reserved for the untouched test. The three models and two affine controls were locked before test rendering began. **Training and the two existing regression paths are complete. The untouched test and Enfusion integration proof remain in progress.**

On the previously difficult partitioned room, the new scene model lowers mean log-radiance error by 50.2% against the source and 12.0% against the new scene-feature affine control. Marking contrast improves. The original specialized model still performs better on its own room. These are regression results on previously inspected paths, not evidence from the untouched test.

## Regression comparisons

Every clip contains all 32 frames of its path: source, the named model and the independent reference. Panels retain their original 480 × 270 pixels. The 20 FPS encoding gives 1.6 seconds of playback; it does not measure inference speed. Expand each comparison to inspect the other input variants.

<figure class="motion-comparison">
<video controls playsinline preload="none" poster="media/diversity-new-room-scene-poster.png" width="1440" height="302" aria-label="Partitioned room: source, full scene-input model, independent reference"><source src="media/diversity-new-room-scene.mp4" type="video/mp4"><a href="media/diversity-new-room-scene.mp4">Download comparison</a></video>
<figcaption>Partitioned room · full scene inputs</figcaption>
</figure>

<details><summary>Partitioned room: other inputs</summary>
<figure class="motion-comparison"><video controls playsinline preload="none" poster="media/diversity-new-room-relative-poster.png" width="1440" height="302" aria-label="Partitioned room: source, model without absolute position, independent reference"><source src="media/diversity-new-room-relative.mp4" type="video/mp4"><a href="media/diversity-new-room-relative.mp4">Download comparison</a></video><figcaption>Without absolute world position</figcaption></figure>
<figure class="motion-comparison"><video controls playsinline preload="none" poster="media/diversity-new-room-rgb-poster.png" width="1440" height="302" aria-label="Partitioned room: source, RGB-only model, independent reference"><source src="media/diversity-new-room-rgb.mp4" type="video/mp4"><a href="media/diversity-new-room-rgb.mp4">Download comparison</a></video><figcaption>RGB only</figcaption></figure>
</details>

<figure class="motion-comparison">
<video controls playsinline preload="none" poster="media/diversity-known-room-scene-poster.png" width="1440" height="302" aria-label="Original room: source, full scene-input model, independent reference"><source src="media/diversity-known-room-scene.mp4" type="video/mp4"><a href="media/diversity-known-room-scene.mp4">Download comparison</a></video>
<figcaption>Original room · full scene inputs</figcaption>
</figure>

<details><summary>Original room: other inputs</summary>
<figure class="motion-comparison"><video controls playsinline preload="none" poster="media/diversity-known-room-relative-poster.png" width="1440" height="302" aria-label="Original room: source, model without absolute position, independent reference"><source src="media/diversity-known-room-relative.mp4" type="video/mp4"><a href="media/diversity-known-room-relative.mp4">Download comparison</a></video><figcaption>Without absolute world position</figcaption></figure>
<figure class="motion-comparison"><video controls playsinline preload="none" poster="media/diversity-known-room-rgb-poster.png" width="1440" height="302" aria-label="Original room: source, RGB-only model, independent reference"><source src="media/diversity-known-room-rgb.mp4" type="video/mp4"><a href="media/diversity-known-room-rgb.mp4">Download comparison</a></video><figcaption>RGB only</figcaption></figure>
</details>

Posters use the preselected frame 16. A 32-pixel label band sits above each image. H.264 CRF 16 and 4:2:0 chroma alter encoded pixels; no frames are scaled, interpolated, dropped or retimed. Exact PNG comparisons: [partitioned room](media/diversity-new-room-scene-poster.png), [original room](media/diversity-known-room-scene-poster.png). The [previous models and their failures](lighting-motion.md) remain available unchanged.

## Measurements

Mean per-frame RMSE in `log1p` scene-linear RGB against the independent reference. Lower is better. Each column includes all 32 frames.

| Method | Original room | Partitioned room |
| --- | ---: | ---: |
| Source | 0.025089 | 0.028890 |
| New affine, scene inputs | 0.013060 | 0.016353 |
| New affine, RGB | 0.016676 | 0.018129 |
| New full scene model | 0.011487 | **0.014385** |
| New model without absolute position | 0.012990 | 0.014829 |
| New RGB-only model | 0.014083 | 0.017292 |
| Previous scene model | **0.007025** | 0.021352 |
| Previous RGB-only model | 0.013003 | 0.018059 |

The full-input candidate passes the declared spatial, boundary/post, contrast and temporal non-regression checks on the partitioned regression. Its mean marking-contrast error falls from 0.019463 in the source to 0.002117; the previous scene model scored 0.030555. The new affine scene control is better on this contrast measure at 0.001495. The RGB-only model still worsens contrast to 0.026733.

No frame breaches the candidate's source-relative boundary or thin-post tolerance on either path. The original room has no marking board: its contrast check is untested, represented as false in the strict all-checks report. It must not be described as a measured contrast failure. The candidate's average error in this room remains worse than the previous specialized model.

The display-space ranking differs: RGB-only has slightly lower mean 8-bit display error than the scene model in the partitioned room, 1.386 versus 1.435 code values. The selected metric and candidate were fixed before evaluation; this result does not change selection.

Temporal error increases by about 0.18% on the original path and 0.11% on the partitioned path, within the declared 2% tolerance. This establishes no temporal improvement. These regression paths retain their original 1,024-sample references and sampling-noise limitation. The untouched test uses 8,192 samples in every source and both references.

## Locked experiment

| Split | Original layouts | Cases |
| --- | --- | ---: |
| Training | Corner gallery, covered court, staggered workshop, split passage | 48 |
| Validation | Offset loading bay | 12 |
| Untouched test | Cross-courtyard camera/light path | 48 frames |

Each layout includes corners, occluding geometry, reflective objects, geometric markings and thin posts. The material library remains shared. These are synthetic original assets, without game geometry, textures or photographic training data.

All variants receive the same 393,216 training pixels, 98,304 validation pixels, minibatch indices, 10,000 optimizer steps and checkpoint schedule. Hidden layers remain 32 × 32; input-layer sizes differ. Source/reference fitting renders use 2,048 samples and differ only in diffuse-bounce depth, 1 versus 12. Validation also retains a second reference seed.

| Variant | Parameters | Selected step | Validation residual MSE |
| --- | ---: | ---: | ---: |
| Full scene inputs | 1,827 | 10,000 | 0.000050234 |
| Without absolute position | 1,731 | 8,750 | 0.000052614 |
| RGB only | 1,283 | 9,250 | 0.000097690 |

Validation selected the full-input model. Definitions were committed in `b76dde4`; the model lock was committed in `780a24e` before test rendering. Test and regression images cannot alter weights, normalization, selection or thresholds.

The untouched-test gate requires at least 5% mean error improvement over source and both new affine controls; no frame may worsen boundary/post error by more than 2% or marking-contrast error by more than 0.002 weighted-log units. Mean temporal error may increase by at most 2%. A gain whose measured sensitivity to the reference seed exceeds half that gain is inconclusive. Complete test clips and failures will be added after evaluation.

## Enfusion work

Three isolated Workbench resource probes compiled and completed. They found town locations and vehicle/character resource names, plus 40 readable materials under `Common/PostProcess`. The resource database search omitted some materials that the documented file interface could read. A built-in HDR material declaration does not establish a custom neural shader interface.

A screenshot-to-widget and external CPU file-return probe is prepared; its Workbench execution is pending. Even successful UI presentation would leave scene-linear inputs, surface buffers, synchronization, HUD/scopes and a supported scene-composition stage unresolved. Varied actual Arma environments—including cities, interiors, vegetation, vehicles, characters and objects—remain required for the integration work.

## Reproduce

The [frozen definition](https://github.com/ethan03805/enfusion-neural/blob/main/scenes/lighting-diversity-v1.json), [model lock and model card](https://github.com/ethan03805/enfusion-neural/tree/main/models/lighting-diversity-v1), [fit evidence](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/lighting-diversity-fit-v1.json), [all regression metrics](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/lighting-diversity-regression-v1.json), [video hashes](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/lighting-diversity-regression-video-v1.json) and [resource-probe evidence](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-resource-probes-v1.json) preserve the experiment's scope.

```powershell
python scripts/evaluate_lighting_diversity.py --scope regression --models models/lighting-diversity-v1 --regression-root experiments/local/lighting-motion-v1 --out experiments/local/diversity-regression-recheck
blender --background --factory-startup --python-exit-code 1 --python scripts/display_lighting_study.py -- --root experiments/local/diversity-regression-recheck --renders experiments/local/lighting-motion-v1
python scripts/summarize_lighting_diversity.py --root experiments/local/diversity-regression-recheck --out experiments/local/diversity-regression-recheck/report.json
python scripts/video_lighting_diversity.py --root experiments/local/diversity-regression-recheck --report experiments/local/diversity-regression-recheck/report.json --out experiments/local/diversity-regression-recheck-videos
```

Use the existing documented Python/OpenEXR, Blender and FFmpeg environment. Raw EXR files and generated scene workspaces stay local. The lighting graph still has no native inference timing or proven live Enfusion mapping.
