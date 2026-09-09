# Handoff

Updated 9 September 2026. Milestone: the locked full-input model passes the 48-frame untouched synthetic test. All three test clips and both regression paths are retained. The Enfusion integration proof remains in progress. Read [objectives](vision.md) before choosing the next model or performance target.

## Latest interface review

The [interface audit](integration.md#interface-audit) covers 8,984 installed full interface pages and 73,747 own-member rows. The index-only pass omitted static methods; full-page controls now explicitly include them. Two custom-GPU keyword matches are unrelated log-buffer and spline methods. The review found no supported model entry point in the inspected declarations, without claiming that private or differently named interfaces cannot exist. The exact [20-feature contract](integration.md#feature-and-execution-requirements) distinguishes scene-linear radiance, visible positions, shading normals and evaluated material values from screenshots, entity metadata and collision traces. Coordinate and single-light semantics also require validation.

`evidence/enfusion-renderer-interface-v1.json` binds both SDK inventories, reviewed signatures, unchanged model code/lock, the prior index-only limitation and a retained source-encoding failure. Completed audit session 5123 is terminal; earlier sessions 39811 and 40094 are also terminal. Raw roots are `renderer-interface-audit-v1`, `renderer-interface-audit-v2-failure` and `renderer-interface-audit-v3` under `experiments/local/`. No Workbench/GPU process was launched and no scene, model or threshold changed. The next required evidence is a specific supported interface/sample; the unsent Bohemia inquiry remains pending its existing authorization request. Keep the full goal active and do not repeat unchanged image-return failures.

## Latest native model experiment

The [lighting GPU implementation](lighting-gpu.md) passes all 21 numerical size/variant checks and all 112 retained full-model test/regression comparisons. The shader performs normalization, both hidden layers, bounded residual and linear reconstruction. Alpha and invalid-pixel source fallback are exact. The 48-frame test and partitioned-room path pass the original fidelity gates; the original room has no marking panel and retains an untested contrast gate. The old specialized model remains better on that room. Test temporal error is 0.735% above source, within the original 2% limit; this is not temporal improvement.

At 1440p the full-input graph's dispatch p50/p95 is 0.96208/1.96096 ms across 100 measurements after ten warmups. One upload takes 13.4095 ms and one readback 3.76312 ms; setup includes 3,775.76 ms and the complete native process takes 4,070.42 ms for all 110 dispatches. The prepared source/target default buffers total 450 MiB. Features are constructed on CPU; this is neither frame time nor a live memory-budget result.

`evidence/lighting-gpu-v1.json` binds all controls, raw output hashes, unchanged models/gates, complete per-frame metrics and initial failures. The original 4K RGB-only shader exceeds the residual bound by one FP32 step at one channel; the separately declared clamp follow-up passes. An earlier disk-full input-write failure is retained. Numerical input recipes and executed source snapshots reproduce removed temporary inputs exactly. Original scene EXRs and GPU output records remain intact. The later packing guard rejects FP32 overflow without changing any executed shader bytes.

All jobs are terminal: initial session 7872, remainder 8448, corrected smoke 3669, frame evaluation 37803 and bootstrap regression 48802. Do not restart them. Raw roots are `lighting-gpu-smoke-v1`, `lighting-gpu-smoke-remainder-v1`, `lighting-gpu-smoke-v2`, `lighting-gpu-frames-v1` and `lighting-gpu-v0-smoke-v1`, under `experiments/local/`. The existing OpenEXR dependency is in `experiments/local/reference-python`; no package was installed. Disk space remains limited; preserve source data and use the recorded transfer-buffer retention policy. The CPU suite passes 70 tests, all six bootstrap GPU regression sizes pass, and twelve invalid native contracts are rejected before GPU setup.

Next: a supported Enfusion feature/execution contract, continued independent color-transfer controls, actual Arma model/reference/motion evaluation and complete-frame measurement. The native graph closes the standalone implementation requirement only. Bohemia contact remains drafted and unsent with unanswered authorization; do not repeat the question or unchanged failed screenshot/widget routes. The site has 25 pages, 75 reviewed PNGs and 12 videos; prior comparison clips remain explicitly CPU outputs.

## Previous native effect experiment

The [color-lookup controls](color-lookup.md) now visibly affect the actual Enfusion camera export. Native schema inspection finds `ColorGradingEffect.ColorTable`; all three original 16³ compiled volumes match every source RGBA voxel. The initial priority-1000 identity request is explicitly rejected. A separately committed priority-19 follow-up completes all seven validations/captures with matching material readback and request order. The native getter's trailing `0` field is preserved rather than silently discarded.

The constant [51, 102, 204] lookup produces a uniform [123, 169, 231] image. Visible response passes; direct RGB8 display mapping does not. Identity/inversion/constant/removal CPU-hypothesis MAE values are 1.2856/69.7983/55.3333/0.4741. All three off-repeat pairs differ, with MAE 0.5608–2.4749 and maximum channel difference 194. No accuracy gate, motion fidelity or trained-model integration follows. Removal is requested immediately after application, before settling.

All nine retained frames were inspected at 2560 × 1440. `evidence/enfusion-color-lookup-v1.json` binds the build, read-only schema/inventory, native captures, all numerical comparisons and `enfusion-color-lookup-review-v1.json`. It retains the silent-inventory callback failure and both initial priority-1000 captures. Raw roots are `color-lookup-{build,schema,inventory}-v1`, `color-lookup-inventory-v2`, `color-lookup-{off,identity}-v1`, and `color-lookup-{off,identity,inversion,constant,removed,off-repeat2,off-repeat3}-v2`, under `experiments/local/`. All jobs are terminal, including batch session 58057; do not restart them. The CPU suite passes 65 tests. Nine unchanged PNGs bring the documentation to 75 PNGs and 12 videos across 24 pages.

The color track still needs separately declared constants and ramps, frozen numerical limits before reserved checks, and dynamic activation/removal, cuts, exposure changes and a second resolution. The subsequent [native lighting result](lighting-gpu.md) establishes standalone GPU/CPU agreement. Supported engine inputs/execution, actual-Arma model/reference/motion tests and complete-frame timings remain required. No model, earlier calibration fit or fidelity threshold changed. The Bohemia inquiry remains drafted and unsent; do not repeat the unanswered authorization question or unchanged failed screenshot/widget routes.

## Previous calibration experiment

The [point-light calibration](light-calibration.md) completed eight native captures and four 4,096-sample Cycles renders. The committed two-coefficient mapping uses only one patch at LV 8, 10 and 12. Seven of 22 reserved patch checks fail: the floor reaches 29.95 RGB8 MAE against a limit of 10, and the fitting patch at a reserved intensity reaches 10.51 against 5. The separate back-wall patch passes at all five settings. Object identity, patch sampling noise and fit-patch clipping checks pass; the calibration candidate does not.

All images were inspected at full resolution. Twelve additional published PNGs retain every engine capture and all four mapped reference images. The historical `direct` reference role permits one bounce and already contains indirect illumination. Neither comparison is neural output or an accepted Enfusion appearance-training pair. The three LV 10 repeats have whole-image MAE at or below 0.00021449 and maximum channel difference 19; none is exactly identical. Static repeatability does not prove motion stability.

Portable evidence is `evidence/point-light-calibration-v1.json`, with the fit lock and both visual reviews alongside it. Raw native roots are `point-light-calibration-{off,lv8,lv9,lv10,lv11,lv12,lv10-repeat2,lv10-repeat3}-v1`; reference and analysis roots are `point-light-reference-v1` and `point-light-calibration-analysis-v1`, all under `experiments/local/`. Native, Blender and queued analysis jobs are terminal and successful as operations. Do not restart them. No model or threshold changed. The suite has 62 CPU tests; the site has 23 pages, 66 PNGs and 12 videos.

The subsequent [color lookup control](color-lookup.md) establishes visible effect response, while its display-color mapping remains unresolved. Supported scene inputs, a complete lighting-model implementation, actual Arma model/reference/motion tests and complete-frame performance remain required. Environment/reflection and material/color isolation are still needed before using engine/reference pairs for training.

## Previous lighting controls

The [room-lighting controls](room-lighting.md) completed all five planned native captures and one separately declared clipping follow-up. The fixed-exposure neutral back-wall mean is 0 at disabled/LV 10 defaults and 221.65 at LV 12. Requesting clipping bias −10 restores the LV 10 region to 102.15 without changing light intensity or camera exposure. Three independent LV 12 captures differ by at most 3 RGB8 values, with all-pair mean errors at or below 0.00000281. They are not exactly identical and do not establish motion stability.

All native validations and captures succeeded. The disabled light reports radius −15 for requested +15; the signed readback check remains false. Intensity/color/attenuation/clipping values are requests without getter verification. Hard black shadows and coarse reflections remain visible. Night environment light is not isolated, and the original reference uses an area light rather than this point light.

`evidence/enfusion-room-lights-v1.json` binds all six captures and `enfusion-room-lights-review-v1.json`. Raw roots are `material-room-light-{off,low,high,high-repeat2,high-repeat3,low-clip}-v1` under `experiments/local/`. All jobs are terminal. The CPU suite passes 59 tests; six unchanged PNGs bring the documentation to 54 PNGs and 12 videos across 22 pages. Next: a separately versioned point-light reference and fixed-exposure calibration sweep with a declared clipping policy. No model, original plan or fidelity threshold changed. Supported integration, actual-Arma model/reference/motion tests and complete-frame performance remain required.

## Previous material experiment

The [packed-texture controls](material-room.md#packed-texture-controls) built all 18 original TIFFs and completed all four planned captures. Native readback matches the declared material maps and Color values. Original source variants change only roughness alpha or metalness blue. The asymmetric back-wall diagnostic agrees with direct TXO sampling at four declared points; only two colored points distinguish an additional V flip. This narrow diagnostic does not overturn the earlier precision failures.

The center sphere responds visibly to both channels. Its preselected region changes by 32.70 RGB8 MAE for roughness and 41.11 for metalness; these are response measurements, not fidelity scores. The shiny sphere reflects exterior scenery, making surrounding light/reflection control the next task. Roughness/BRDF calibration, exposure/color mapping and an aligned appearance pair remain unfinished.

`evidence/enfusion-room-textures-v1.json` binds the source plan, build/header checks, all four native captures, orientation analysis and `enfusion-room-textures-review-v1.json`. Raw roots are `material-room-textures-source-v1`, `material-room-texture-build-v1`, and `material-room-texture-{orientation,packed,matte,dielectric}-v1` under `experiments/local/`. All native jobs are terminal. Four unchanged reviewed PNGs bring the site to 48 PNGs and 12 videos across 21 pages. No model or threshold changed. Native lighting inference, supported integration, varied actual-Arma model/motion tests and complete-frame performance remain required.

## Implemented and checked

- Original procedural training data and a 251-parameter residual CNN with all weights trained locally.
- Versioned JSON model, bounded residual, independent CPU inference and numerical gradient checks.
- Native D3D12 FP32 inference on the recorded test configuration, including raw timestamps and separate file-pipeline measurements.
- CPU/GPU pixel agreement at 1440p and on an actual Enfusion capture; random-alpha and dimension checks through 4K.
- Enfusion Lab doctor, isolated addon compile validation and visually inspected Arland capture.
- Three diagnostic scene variants with explicit camera, date, time, weather and wind controls; nine independent captures and all nine pairwise comparisons.
- Telemetry and image-hash checks, dataset-group split validation, unaligned image errors and a bounded integer alignment estimate.
- Twenty-five-page Markdown documentation site with system/light/dark themes, still comparisons and synchronized videos; shared agent/human protocol, Linux CPU CI, Windows build/smoke workflow and GitHub Pages deployment workflow.
- Eighty camera-path samples at 2560 × 1440, each with a GPU output checked against the independent CPU reference. One encoded stream keeps before/after playback synchronized. It is a retimed offline sequence, not live performance.
- Camera projection, exposure, environment and selected engine settings readback checks. Three final static repeats and an earlier probe batch remain documented, including nonzero pixel differences.
- Original material room generated with Blender Cycles, limited-bounce source, multi-bounce reference and independent-seed noise check. Exact source/reference depth and object-ID agreement; scene-linear RGBA and auxiliary EXR passes retained locally. This is synthetic data, not an Enfusion/reference pair.
- Seventy-five reviewed PNGs and twelve videos with source records, hashes and attribution. Scaling, label bands and compression are recorded for each video/poster; original source/model frame PNGs remain available.
- Eighteen original lighting cases with paired diffuse-bounce controls, 12 training/two validation/three test/one stress splits within one scene group, and two independent-seed reference checks. A 1,827-parameter scene-conditioned CPU model beats RGB-only and affine controls on the three test cases. Weights, gradients, serialization, features and partitioned inference are checked. See [lighting study](lighting-study.md); no game-frame saving or temporal fidelity is established.
- Read-only [technical feasibility review](feasibility.md) of installed SDK declarations, asset-specific representations, photographs and data-use scope. Material replacement is documented; native scene buffers and output composition remain unverified.
- [Frozen-model scene transfer and motion](lighting-motion.md): 32 frames in the original room and 32 in a new partitioned room, with an independent reference at every frame. No fitting or checkpoint selection on these paths. The scene-conditioned model lowers average error but loses to RGB-only on the new layout and worsens marking contrast. Mean temporal changes are too small relative to sampling noise to establish meaningful stability. Two synchronized source/model/reference clips and the preselected frame-16 stills are published.

Exact observed results and limitations are in [evidence](evidence.md). The source commit and CI/deployment outcomes are visible in the repository history and Actions; do not assume later revisions have the same measurements.

## Reproduce

```powershell
python -m unittest discover -s tests -v
cmake -S native -B build -A x64
cmake --build build --config Release
python -m enr.cli benchmark --model models/bootstrap-v0.json --out runs/recheck
python scripts/gpu_smoke.py
python scripts/build_docs.py
```

Use the prepared environment with the documented dependencies. Reviewed manifests live in `evidence/`. Local captures and full raw workspaces are ignored under `experiments/local/` and `runs/`. The bootstrap training record lives inside `models/bootstrap-v0.json`.

## Active experiment

The [scene-diversity comparison](lighting-diversity.md) has completed 48 training and 12 validation cases across five original layouts, followed by three fixed-budget fits and two affine controls. Validation selected the full-input candidate. `models/lighting-diversity-v1/model-lock.json` was committed before the cross-courtyard test began rendering. Do not retrain, change samples or thresholds, or select a different candidate from test/regression results.

Both published 32-frame paths have been evaluated with all new and old controls. The full-input candidate improves average error, boundaries/posts and marking contrast relative to the source on the partitioned regression. It remains worse than the old specialized model on the original room; that room has no marking panel. Six complete regression clips and all frame metrics are retained. No temporal improvement is established.

The untouched render finished normally with all 144 source/reference passes. Its queued evaluation, display conversion, summary and three videos also completed. The full-input model reduces mean log error 63.1% versus source and 26.6% versus the stronger affine control. Both full and relative-input variants pass the declared test checks; RGB-only fails the aggregate spatial and temporal checks. No variant breaches the per-frame regional limits. The candidate's temporal error increases 0.73%, within the 2% tolerance; this is not a temporal improvement.

Test artifacts are `experiments/local/lighting-diversity-test-v1/`, `experiments/local/lighting-diversity-test-evaluation-v1/` and `experiments/local/lighting-diversity-test-video-v1/`. Portable reports are `evidence/lighting-diversity-test-v1.json`, `evidence/lighting-diversity-test-variants-v1.json` and `evidence/lighting-diversity-test-video-v1.json`. Every decoded video frame and all preselected frame-24 posters were inspected. The model lock and thresholds were unchanged. The Blender and evaluation jobs are terminal; do not restart or duplicate them. Serialize subsequent GPU experiments.

The completed local fit is `experiments/local/lighting-diversity-fit-v1/`; CPU model fitting is `experiments/local/lighting-diversity-models-v1/`; regressions are `experiments/local/lighting-diversity-regression-v1/` and `experiments/local/lighting-diversity-regression-v1-videos/`. Portable reports are `evidence/lighting-diversity-fit-v1.json`, `evidence/lighting-diversity-regression-v1.json` and `evidence/lighting-diversity-regression-video-v1.json`. The subsequent [GPU implementation](lighting-gpu.md) verifies all 112 frames without changing these frozen artifacts.

Three read-only Workbench resource probes compiled and completed before the test render. `evidence/enfusion-resource-probes-v1.json` records their hashes and counts. Resource names and map locations are available; no live neural bridge was proven. The `ENR_ImageBridge.c` and optional entity-placement scripts passed silent ScriptEditor validation in run `20260909T055234-51d147e1ad`, without loading a world. `evidence/enfusion-image-bridge-compile-v1.json` records the actual script hashes. Three texture-copy runtime attempts are terminal: two timed out and the third crashed after making the widget visible. `evidence/enfusion-image-bridge-v1.json` retains their failures; none proves image return. The external CPU controls and verifier tests pass, including rejection of a one-channel pixel error, a failed widget under a successful capture, and altered evidence. The copied-texture route has failed under three scheduling variants. Test a separate file-return route only with an explicit new hypothesis and preserve its outcome. Summarize each run with `scripts/summarize_enfusion_image_bridge.py`; exact UI pixels cannot certify a scene render pass. A successful screenshot/UI roundtrip would still leave the lighting model's scene buffers and presentation contract unresolved.

The active goal also requires varied actual Arma tests, including cities, interiors, vegetation, vehicles, characters and objects. Reviewed source scouts now cover Everon town streets, a warehouse interior, vegetation, a factory and placed vehicle/character entities. Neural fidelity on these environments, aligned appearance targets and supported integration remain required; source captures and synthetic results cannot close them.

The raw identity attempt in `experiments/local/image-bridge-identity-v1/` is also terminal. It timed out before its raw screenshot callback, leaving no source PNG or CPU output. The runtime evidence includes this fourth failure. Check the latest milestone below and current CI for test and media counts.

Prepared local scout configs are under `experiments/local/arma-diversity-scouts-v1/` for Beauregard, Arleville, a harbour and an initial Everon overview. Their camera framing is unverified, and Arland towns do not replace the required larger city test. The image probe accepts `--config` and optional `--entities` for a vehicle/rifleman placement test using resource names found by the inventory. The corrected placement script has now spawned an upright M998 and standing rifleman in Saint-Philippe; both are visually verified in the source scene. The probe loader requires `--world-inventory` to bind an additional world to a completed native inventory; the default sequence contract still restricts callers to Arland.

A search-only inventory now completes with normal ScriptEditor initialization and no world load. It observed eight world resources, including `{853E92315D1D9EFE}worlds/Eden/Eden.ent`. Raw evidence is under `experiments/local/resource-inventory-module-v2/`; the portable report is `evidence/enfusion-world-inventory-v1.json`. Two silent attempts and one earlier normal-startup timeout remain retained. The additional-world loader verifies this distinct operation's manifests, scripts, natural exit and callback/search completion. The CPU suite includes rejection of changed manifests, incomplete callbacks and a native capture failure accompanied by otherwise valid image files.

Everon loads in the WorldEditor search-only probe. `evidence/enfusion-everon-scout-v1.json` records the initial coast-and-sky overview and an earlier material-traversal timeout. The revised query completed with 170 named locations among 650 descriptors. `scripts/capture_enfusion_scout.py` then captured ground-level sources at observed locations. `evidence/enfusion-arma-scenes-v1.json` retains the Saint-Philippe garden, two failed entity placements, corrected upright placement, four factory views, four interior views and four Montignac street views. All were visually inspected. Original warehouse and street views contain unsupported-looking objects. The completed source-visibility controls restore the observed detail with a longer per-view hold, while retaining those earlier failures. The exact engine mechanism remains unverified; no capture is an aligned appearance reference.

## Original acceptance

Design a scene-diversity and input-ablation experiment. Add multiple original training layouts and reserve a new untouched scene for evaluation. Compare the current feature contract with an ablation that excludes absolute world position under the same training budget. Keep current weights and both published motion paths as regression controls; these paths have now been inspected and must not serve as the sole unseen test for the next model.

Acceptance: declare groups before fitting, beat identity and simple baselines on the untouched scene, preserve marking contrast and boundary/visibility tests, and use higher-convergence references to distinguish temporal behavior from sampling noise. The locked diversity model passes the declared synthetic test gates. That result does not establish broad Arma asset fidelity or temporal improvement.

In parallel, identify an authoritative supported renderer extension for a minimal identity/inversion control. Verify source color, required surface inputs, synchronization and presentation before scaling Reforger asset training. The [feasibility report](feasibility.md) separates documented declarations from tested capabilities. No native lighting-model implementation or timing exists yet.

Current lighting evidence: `experiments/local/lighting-study-v1/` (18 rendered cases), `experiments/local/lighting-fit-v1b/` (published weights and predictions), and `evidence/lighting-study-v1.json` (all metrics and source records). Earlier `lighting-fit-v1/` is retained; it has identical numerical outputs before adding the portable JSON model contract. Both fits use the same fixed plan and hyperparameters.

Current motion evidence: `experiments/local/lighting-motion-v1/` (192 source/paired-reference/independent-reference renders), `experiments/local/lighting-motion-evaluation-v1/` (all frozen model outputs), and `experiments/local/lighting-motion-video-v1b/` (published encoding). The earlier video directory is retained and has identical image/video bytes before normalizing portable report line endings. Reports are `evidence/lighting-motion-v1.json` and `evidence/lighting-motion-video-v1.json`. The renderer finished normally; it launched no Workbench process.

## Prior capture work

Resolve internal Workbench viewport render scale and FSR. The diagnostic save succeeded, and a black-frame control confirms that the isolated file loads. Neither the diagnostic scale presets nor the settled workspace controls established the required viewport effect. The separate render-target callback rejected export. See [capture controls](capture-controls.md#diagnostic-investigation) and `evidence/viewport-probes-v1.json` before repeating these attempts.

Next acceptance criteria: identify a supported setting or diagnostic that belongs to the main viewport, obtain its effective internal dimensions and FSR state, then demonstrate a corresponding image change with a reduced-resolution control. Only after that should a full-resolution, FSR-disabled preset receive three independent repeat captures. `scripts/probe_viewport.py` reproduces the current unresolved probes; its successful exit means the investigation ran, not that viewport controls were verified.

The subsequent native UI inspection and one post-startup `UserSettingsChanged()` probe did not resolve this. Their observations and run hashes are retained in `evidence/viewport-followup-v1.json`. The isolated inspection window was closed normally; no other editor was changed. No accepted scale/FSR preset is available yet.

Next, import the original material-room geometry into an isolated Enfusion scene and validate matching camera, materials, light and color conventions before using engine/reference pairs for training. The accepted synthetic pair only validates the reference-generation method. See [material room](material-room.md) and [roadmap gate 02](roadmap.md#02-reference-scenes-and-appearance-data). The supported renderer bridge remains a separate research task.

Current local evidence: `experiments/local/motion-static-v1c/` for final repeats; `experiments/local/motion-v1b/runs/20260909T003650-5d8d09c360/` for the 80-frame sequence; `experiments/local/motion-output-v1/` for GPU outputs and video; `experiments/local/material-room-v1d/` for the accepted synthetic pair. Earlier probes and failed runs were retained. Portable reports are `evidence/capture-controls-v1.json`, `evidence/motion-v1.json` and `evidence/material-room-v1.json`.

The first measured reference batch is retained locally under `experiments/local/reference-v1/`; its reviewed numerical report is `evidence/reference-scenes-v1.json`. All camera/environment checks passed, but every scene had nonzero pixel variation. These captures remain diagnostic data, not supervised appearance targets.

The project priorities are visual fidelity, photorealism without scene/identity distortion, and a 1440p/20 FPS playable floor on the recorded test configuration. Do not revert to the earlier 60 FPS reconstruction-first proposal. The bootstrap CNN is a control for learning and GPU execution, not the final model architecture.

## Publication and current native probes

PR #6 merged at 97571dcc3458bba8f00a3e68cf84152b3c808a60. Linux/Windows CI and Pages succeeded. Live HTML contains all nine diversity/regression clips; the six new test video/poster files match the reviewed local bytes exactly. The complete synthetic comparison is published, while the full integration and varied-Arma goal remains active.

The ordinary screenshot file route exports RGB8, which the first worker rejected under its RGBA-only contract. The retry explicitly preserves RGB code values and supplies opaque alpha, recording that source alpha is absent. The CPU identity operation and local PNG load completed, but the widget rejected raw-data readback. The full bridge check remains false. Source, worker output and native failures remain local and in the portable reports.

The inversion control also loads a correctly inverted CPU file but rejects widget readback. Its final ordinary export remains the normal scene, with mean RGB difference 129.20 code values against the worker output. The identity control differs by 5.01. `evidence/enfusion-file-return-v1.json` verifies the CPU operations independently while retaining all bridge checks as false. No live UI/display stage or scene renderer is inferred from the widget visibility flag.

All listed render, evaluation, bridge and scout jobs are terminal. Do not restart the frozen synthetic evaluation or repeat failed callbacks without a new supported hypothesis. The source-visibility work is on `experiment/source-visibility`; reviewed source PNGs are byte-for-byte copies with manifest hashes. Raw runs remain ignored.

Immediate next acceptance: identify an authoritative supported renderer extension and verify identity/inversion at its intended stage, followed by the lighting feature mapping. Separately, extend the tested longer hold to short real-scene motion paths and aligned engine/reference lighting pairs, checking visibility in every new view. Native lighting execution and complete-frame timings follow a valid input/output contract. See the [roadmap](roadmap.md) for the full unfinished goal.

## Source-visibility result

Ten isolated controls completed with natural addon-validation exits and four checked captures each. The initial plan compares fresh repeats, 30-second initial settle and 120-update per-view hold in the warehouse and Montignac. Two further long-hold runs per scene were declared after inspecting the initial six; all 40 new frames were visually reviewed. All jobs are terminal.

The longer hold restores the observed shelf supports, building surfaces and sign/board detail in all three runs per scene. Longer initial settling with six updates does not. Use 120 updates as a candidate setting for these offline fixtures, not as a universal asset-readiness guarantee or GPU completion fence. Full-image and declared-region differences remain in `evidence/enfusion-source-visibility-v1.json`; explicit observations are in `evidence/enfusion-source-visibility-review-v1.json`. The source report binds both plans, run/script/config/image hashes and actual simulation intervals. The one runtime-writable Workbench UI settings file retains initial and final hashes separately.

Raw runs are under `experiments/local/source-visibility-v1/`. All earlier anomalous PNGs remain in the site; two new unchanged first-long-hold PNGs add warehouse/town sliders. The warehouse follow-up differences are 0.0021–0.0160 RGB8 MAE per view; Montignac is 0.1451–2.0184. These are source variation measurements. The full goal still requires supported integration, aligned lighting targets, real-scene model/motion checks and native complete-frame timings.

A technical inquiry is drafted locally at `experiments/local/bohemia-renderer-questions.md`. It has not been sent; explicit authorization to contact Bohemia is pending. Do not substitute repeated failed screenshot/widget callbacks for an authoritative renderer extension.

## Material-room import follow-up

The [original-room import](material-room.md#engine-import-controls) now works. Earlier probes requested `Workbench.Exit` while an asynchronous rebuild was still queued. Keeping the private editor alive produces complete geometry from the unchanged FBX and the derived LOD0 version; a fresh project also builds successfully. Three separate natural-exit loads each report seven material regions. All seven earlier failure records remain unchanged, including the weak check that accepted an empty resource.

`evidence/enfusion-room-geometry-v1.json` binds the read-only metadata inspection, three builds, three loads, two vertex comparisons and two captures. All 12 meshes and 18,390 vertices match the original axis-mapped positions with maximum coordinate error below one micrometre. Native bounds and pitched-camera/projection readback pass. Both captures visibly show the room, spheres, box, plinth and three posts. Materials are default white under outdoor lighting; an aligned appearance pair and renderer integration remain unverified. One variable/type-name compilation failure is retained before the successful captures.

All runs are terminal. The original-source controls are under `experiments/local/material-room-original-live-build-v1/`, `material-room-original-load-v1/` and `material-room-original-geometry-v1/`; independent fresh builds/loads are in `material-room-fresh-build-v1/` and `material-room-fresh-load-v1/`. The derived control is in `material-room-live-build-v1/`, `material-room-load-v1/` and `material-room-geometry-v2/`. Geometry reports and their executed Blender script snapshots are retained alongside these directories. Continue with material and illumination calibration, not repeated empty-import probes.

The CPU suite has 53 tests. The site has 21 pages, 42 reviewed PNGs and 12 videos; the new image is an unchanged original-room engine capture with its appearance limitations labeled.

## Material schema and face-corner checks

`evidence/enfusion-room-surface-v1.json` verifies a native read-only material-container inspection and two offline Blender comparisons. The inspection compiles and exits naturally, exposes 142 `MatPBRBasic` fields, and retains all original assets unchanged. `Color` has a white default; actual scalar readback gives `RoughnessScale` and `MetalnessScale` as 1. Packed-map and color semantics remain unverified. Raw native evidence is `experiments/local/material-room-schema-v1/`.

All 18,570 faces and 73,872 corners retain connectivity and named material assignments. Winding consistently reverses under the axis reflection. The strict normal/UV check fails for the spheres and posts: maximum normal component error is 0.00005004 (0.0044° angular error), and maximum UV error after V inversion is 0.000005. The limits remain 0.00002 and 0.000002. The initial report and follow-up script snapshots are retained as `material-room-surface-check-v1` and `v2` under `experiments/local/`.

The follow-up adds decimal-grid diagnostics without changing results or thresholds. All TXO normals occupy a four-decimal grid and UVs a five-decimal grid, consistent with serialization precision. Rounded source values still differ at some sphere ties; compiled XOB precision and raster shading are untested. Do not rerun unchanged probes to seek a passing label. These jobs are terminal, and no material edits, new captures or model changes were made.

Next: original asymmetric texture and controlled-light captures to verify texture orientation, material/color response and silhouettes. Then calibrate illumination/exposure for a valid engine/reference pair. The supported renderer interface, real Arma model/motion tests and native lighting graph remain unfinished.

## Material color response

The [color control](material-room.md#material-color-control) changes only seven `MatPBRBasic Color` constants in fresh isolated addon copies. White and original-color cases share the same camera/environment/configuration. Both compile, capture and pass native RGBA readback; predeclared left/right wall color-dominance checks pass. The red/blue walls, brown box/right sphere, neutral room surfaces and dark posts are visually verified at full resolution. Packed-map parameters remain default, and the intended metal sphere remains visually nonmetallic.

`evidence/enfusion-room-color-v1.json` binds the plan, original imported assets, material edits, driver/native script snapshots, logs, settings and sample images. `material-room-color-white-v2` and `material-room-color-reference-v1` under `experiments/local/` are successful and terminal. The earlier `material-room-color-white-v1` timed out after the reader used a mesh slot name as a resource path; its native failure and validation remain retained. The corrected reader resolves slots through verified `.emat.meta` GUIDs.

Two unchanged PNGs add a labeled slider to the material-room page. The site now contains 44 PNGs and 12 videos across 21 pages. No training weights or thresholds changed. Next import asymmetric original packed textures, check UV orientation and roughness/metalness response, then match the light/exposure/color convention. Native renderer integration and real Arma model/motion fidelity remain unfinished.
