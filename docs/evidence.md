# Evidence

The [reference scene pack](reference-scenes.md#first-measured-batch) adds nine repeated captures with verified camera/environment settings and measured image differences. The earlier model execution results follow below.

Measured locally on 8–9 September 2026. The results establish an offline neural path on the recorded test configuration. They do not establish photorealism or live game performance.

## Native lighting graph

The subsequent [interface review](integration.md#interface-audit) inventories installed SDK declarations and maps the graph's 20 inputs to the unresolved engine requirements. It is read-only documentation evidence, not a runtime integration test. Its [portable record](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-renderer-interface-v1.json) retains the incomplete index-only pass and the corrected source-encoding failure.

The [lighting GPU result](lighting-gpu.md) verifies all three locked variants on 21 numerical controls through 4K, plus the full model on every one of the 48 test and 64 regression frames. All native outputs match the CPU tolerances with exact alpha and invalid-source fallback. The test's original fidelity gates pass. Its temporal error is 0.735% above source, within tolerance. The original room's missing contrast panel and loss to its older specialized model remain documented.

Full-input 1440p dispatch p50/p95 is 0.962/1.961 ms. One upload/readback pair adds 17.173 ms, with 3,775.76 ms setup and a 4,070.42 ms native process for all 110 dispatches. These are standalone timings on prepared features, not game frame time. A disk-write failure and the initial one-step residual-bound violation remain in the [complete evidence](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/lighting-gpu-v1.json). Six unchanged RGBA8 hardware checks are retained in the [bootstrap regression record](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/lighting-gpu-v0-regression-v1.json).

## Camera color lookup

The [static lookup controls](color-lookup.md) verify three original compiled 16³ volumes and visible native camera effects. Seven priority-19 captures pass native request/readback checks. A constant [51, 102, 204] lattice produces a uniform [123, 169, 231] export, so visible application passes while direct display-code mapping fails. Identity, inversion, constant and removal CPU-hypothesis MAE values are 1.286, 69.798, 55.333 and 0.474. Three off captures vary by 0.561–2.475 MAE, with maximum channel difference 194. No color-accuracy or motion gate passes by inference from these diagnostics.

All nine images, including the rejected priority-1000 identity control and its baseline, are retained. A silent inventory callback failure is also recorded before the successful native inspection. This effect runs no trained model and supplies no scene buffers or complete-frame performance result. [Metrics, original build checks and native provenance](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-color-lookup-v1.json).

## Point-light calibration

The [calibration comparison](light-calibration.md) retains eight successful native captures and four independent-seed reference passes. Its frozen brightness mapping fails seven of 22 reserved checks. Worst floor error is 29.95 RGB8 MAE against a limit of 10. Object identity, reference-patch noise and fit-patch clipping checks pass; they do not override the response failure. Three independent LV 10 captures are close but not identical, with maximum channel difference 19. This is a static calibration diagnostic, with no neural inference, accepted appearance pair or live performance claim.

[Complete metrics and hashes](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/point-light-calibration-v1.json) · [Frozen fit](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/point-light-calibration-lock-v1.json)

## Neural GPU execution

| Input | Dimensions | Dispatch p50 | Dispatch p95 | CPU comparison |
| --- | --- | --- | --- | --- |
| Procedural fixture | 2560 × 1440 | 0.11816 ms | 0.17368 ms | Pass; max RGB error 1, alpha exact |
| Arland Workbench capture | 1839 × 947 | 0.05664 ms | 0.07968 ms | Pass; max RGB error 1, alpha exact |

Each run contains ten warmups and 100 measured dispatches on the same buffers, including a UAV barrier in each dispatch interval. Native FP32 HLSL executes the trained 251-parameter model. There is no inference runtime or CPU operator fallback in this shader path.

The file pipeline took **764.74 ms** for the 1440p run and **690.43 ms** for Arland. Each value includes startup, shader compilation, 110 dispatches and output export, and excludes the separate CPU reference check. It is not per-frame latency. The current file pipeline is not a playable renderer.

[1440p raw samples and manifest](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/gpu-1440p.json) · [Arland raw samples and manifest](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/gpu-arland.json)

Visual inspection of the Arland output shows exaggerated edges and dark boundaries in foliage compared with the source. The procedural reconstruction model is unsuitable as a photorealism demonstration. Numerical agreement proves that the GPU implements the model; it does not make that model's appearance acceptable. This observed failure motivates the paired appearance data and identity checks in the next gates.

[Inspect the before-and-after comparison](comparisons.md). The published files preserve the original exported pixels and the recorded model output.

Correctness also passed for random RGBA inputs at 1 × 1, 1 × 17, 31 × 1, 127 × 65, 1920 × 1080 and 3840 × 2160. Each comparison checked every RGB value and exact random alpha. These smoke checks prove numerical behavior at those sizes, not acceptable frame times on other GPUs.

The initial [hosted Windows CI run](https://github.com/ethan03805/enfusion-neural/actions/runs/34288593414) passed through 1080p but its 4K, 110-dispatch batch exited with access violation 3221225477 after approximately 34 seconds. The exact driver/device cause is unresolved; this failure was not observed in the separately recorded hardware tests. Correctness smoke tests now use a single dispatch at every size, while full performance runs keep their explicit sample counts. Failed smoke artifacts are retained and uploaded by CI for diagnosis. The original local measurements above predate this separation.

The [follow-up hosted run](https://github.com/ethan03805/enfusion-neural/actions/runs/34288952799) passed single-dispatch comparisons through 4K but identified its adapter as **Microsoft Basic Render Driver**. That is software execution, not GPU hardware evidence. The native selector now explicitly excludes that driver in addition to checking DXGI's software flag. Hosted checks skip when no hardware remains; the separately recorded hardware tests remain the hardware evidence. The earlier full-batch crash has not been characterized as a hardware failure.

## Learning result

Training fits all network weights on the local CPU with seed 7, 1,200 Adam steps and original procedural data. Train scene seeds are 0–11; validation scenes 100–103; test scenes 200–203. No game captures, photographs or downloaded model weights were used in training.

| Held-out scene | Bicubic PSNR | Neural PSNR |
| --- | --- | --- |
| 200 | 24.860 dB | 25.263 dB |
| 201 | 25.479 dB | 26.216 dB |
| 202 | 25.574 dB | 25.857 dB |
| 203 | 24.287 dB | 24.728 dB |

The comparison uses bicubic 0.5× downsampling followed by bicubic upsampling on procedural 256 × 256 scenes. PSNR is calculated in display-referred normalized RGB before output quantization. The test distribution is narrow and contains no temporal sequences. It is not a comparison against FSR, native game rendering or a photorealistic reference.

[Evaluation record](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/evaluation-v0.json) · [Model card](https://github.com/ethan03805/enfusion-neural/blob/main/models/MODEL_CARD.md)

## Enfusion capture

Enfusion Lab 0.1.0 discovered stable game build 24903726 and Workbench build 24870687 from local Steam manifests. This is not a remote update check. The isolated addon validated with natural exit 0.

Arland capture used position [2048,60,2048], direction [1,0,0] and a five-second settle. The 1839 × 947 PNG was visually inspected: terrain, trees and sky filled the frame. Capture outer status succeeded; the tool then terminated its owned Workbench process. Raw logs remain local. The original image is now included in the comparison gallery; the historical capture summary predates its publication.

[Portable capture summary](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-capture.json)

## Still unverified

Live integration, linear/HDR scene color, depth, motion vectors, material buffers, pre-HUD presentation, semantic fidelity, temporal stability, total frame times and live memory budget. No cloud GPU has been rented. No claim of broad Enfusion or multi-vendor support is made.

## Camera path and synthetic reference

The [capture controls](capture-controls.md) report three checked static repeats, an earlier probe batch and the unresolved viewport scale/FSR issue. Final pairwise RGB MAE is 0.379–0.891; earlier probes reached 2.358. Every pair has estimated integer translation [0,0], which does not establish deterministic foliage.

The [viewport investigation](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/viewport-probes-v1.json) records a successful diagnostic save and a black-frame control proving that the settings file loads. Scale/FSR presets and settled workspace controls remain unverified for the main viewport; the separate texture-export callback returned false. Fourteen investigation runs, including failed attempts, remain traceable in the report.

The [motion comparison](comparisons.md#motion) contains 80 paired source/GPU frames. All pass the independent CPU reference with maximum RGB error of one 8-bit value and exact alpha. A four-second, 20 FPS encoded clip is retimed from a sequence spanning 21.762 simulation seconds; offline processing and CPU checks took 116.641 seconds. See the [full frame and video record](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/motion-v1.json).

The [material-room report](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/material-room-v1.json) records exact source/reference depth and object-ID alignment. Independent reference seeds differ by 0.356 RGB code values on average and about 0.497% relative RMSE in scene-linear RGB. This is an original synthetic target-generation test, not neural quality on Enfusion.

## Controlled lighting reconstruction

The [lighting study](lighting-study.md) contains 18 paired synthetic cases at 480 × 270 with equal sample counts and only diffuse-bounce depth changed. The 1,827-parameter CPU network receives original scene features; a smaller RGB-only network and an affine fit provide controls. Mean display RGB error over the three test cases is 2.568 for source, 1.019 for affine, 1.059 for RGB-only and 0.538 for scene-conditioned output. Test cases share the training room/assets and remain a within-scene diagnostic.

The independent-seed test-view reference gives source/model errors of 2.523/0.847; the stress case gives 4.602/1.907. Noise, display roundtrip error, boundary/thin-post metrics, raw render-call timings and all individual cases are retained in [the full evidence](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/lighting-study-v1.json). No native GPU execution, temporal acceptance, independent scene generalization or net engine-frame saving is established for this model.

The [feasibility review](feasibility.md) records inspected SDK capabilities and research precedents separately from demonstrated integration. [SDK hashes and sources](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/feasibility-v1.json).

## Frozen-model scene transfer and motion

The [motion study](lighting-motion.md) evaluates 64 frames without retraining. Mean display RGB error is 2.670 → 0.881 in the original room and 2.954 → 2.335 in the new partitioned room. RGB-only gives 1.520 on the new room. The scene-conditioned model's marking-contrast error increases from 0.0195 to 0.0306 despite lower region-average error. Mean reprojected temporal error is slightly below identity, but five new-room transitions worsen and sampling-noise comparisons exceed the small average difference. No perceptual temporal acceptance is claimed.

Every frame has an independent reference. Paired depth/object IDs match exactly; source-camera self-projection checks pass; temporal correspondence coverage is 88.4–92.6%; display roundtrip error is at most one code value and alpha is exact. [All frame/region/transition records](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/lighting-motion-v1.json) · [Complete encoded frame provenance](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/lighting-motion-video-v1.json).

## Original packed-texture response

The [material-room controls](material-room.md#packed-texture-controls) retain all four captures and all 18 original texture builds. Native map/Color readback and source-channel isolation pass. The declared sphere region changes by 32.70 RGB8 MAE for roughness and 41.11 for metalness. The four-point orientation diagnostic supports direct TXO sampling on the tested back wall. Neither image difference nor hue agreement establishes physical material equivalence or neural fidelity. [Full evidence](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-room-textures-v1.json) retains headers, recipes, hashes, telemetry and scope; the [visual review](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-room-textures-review-v1.json) records exterior scenery reflections and visible coarse/mottled shading.

## Native point-light controls

The [room-lighting comparison](room-lighting.md) retains five planned captures and one clipping follow-up. Neutral back-wall means are 0.00 RGB8 for the disabled/lower defaults, 221.65 at native LV 12 and 102.15 at unchanged LV 10 with requested clipping bias −10. The latter supports the low-intensity clipping hypothesis. Three independent LV 12 captures have all-pair whole-image RGB8 MAE from 0.00000018 to 0.00000280 and maximum channel difference 3. These are response/repeatability measurements, not fidelity or motion results.

All native compile/capture checks pass; the disabled light's raw radius readback is −15 for requested +15, so the signed readback check remains false. No getter verification exists for the recorded intensity, color, attenuation or clipping requests. Hard black shadows and coarse reflection edges remain visible. [Complete evidence](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-room-lights-v1.json) preserves all runs, hashes, region means and pairwise differences. No reference photometry, isolated environment or neural integration is established.

## Disjoint-layout lighting test

The [scene-diversity experiment](lighting-diversity.md) uses four training layouts, one validation layout and one untouched test layout. Validation selected and locked the full-input candidate before its 48-frame test rendered. Mean test log-radiance RMSE is 0.025340 for source, 0.012754 for the stronger affine, 0.009360 for full inputs, 0.009837 without absolute position and 0.013509 for RGB-only. Full and relative-input models pass the declared checks. RGB-only fails aggregate spatial improvement and temporal non-regression; its full clip remains available.

No test frame breaches the source-relative boundary, thin-post or marking-contrast limits. The full model's temporal error rises 0.73%, within the predeclared 2% tolerance; no temporal improvement is established. Test renders use 8,192 samples for every source and both references. All 48 frames, prior models, per-frame measurements, seed sensitivity, model hashes and display conversions are retained in [the full report](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/lighting-diversity-test-v1.json). [All-variant checks](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/lighting-diversity-test-variants-v1.json) apply the same implementation without reselection. [Video provenance](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/lighting-diversity-test-video-v1.json) covers the three complete 2.4-second clips. This evidence establishes the synthetic test result, not live neural rendering or broad game-asset fidelity.

## Real-scene sources and file-return controls

The [Arma source record](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-arma-scenes-v1.json) retains seven runs: a garden, two failed entity placements, corrected vehicle/character placement, and four directions each at the factory, warehouse interior and Montignac street. All images were inspected. The [gallery](arma-scenes.md) publishes six unchanged PNGs, including two source visibility anomalies. No appearance target or neural lighting result is attached to these scenes.

The subsequent [source-visibility controls](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-source-visibility-v1.json) retain 40 new views across ten independent runs, plus all eight original views. Holding each camera direction for 120 world updates restores the observed warehouse supports and Montignac building/sign detail in three runs per scene. Keeping six updates but extending the initial settle to 30 seconds does not. Two new unchanged PNGs provide source comparisons in the gallery; no model is involved. All per-view and declared-region differences are retained. Long-hold repeat differences range from 0.0021–0.0160 RGB8 MAE in the warehouse and 0.1451–2.0184 in Montignac. This supports the fixture setting, not deterministic rendering, an exact internal cause or a valid appearance target.

The report verifies run/config/log/image hashes, immutable addon snapshots, natural script-validation exits, camera/environment/projection and actual update intervals. Workbench writes its initially empty `ENR_Workbench.ini` during execution; that one mutable UI-settings file retains both initial and final hashes, rather than being treated as immutable script input. [Every frame's visual observation](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-source-visibility-review-v1.json) is bound to its image hash.

The [file-return record](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-file-return-v1.json) retains an initial RGB-channel rejection and two exact CPU identity/inversion operations. Both processed files were accepted by the widget loader, but raw-data readback failed. The final ordinary scene captures do not match the processed files. Every bridge verification field remains false; CPU file processing time is not a frame-rate result. See [integration](integration.md) for the remaining contract.
