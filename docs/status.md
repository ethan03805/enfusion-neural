# Handoff

Updated 9 September 2026. Milestone: the locked full-input model passes the 48-frame untouched synthetic test. All three test clips and both regression paths are retained. The Enfusion integration proof remains in progress. Read [objectives](vision.md) before choosing the next model or performance target.

## Implemented and checked

- Original procedural training data and a 251-parameter residual CNN with all weights trained locally.
- Versioned JSON model, bounded residual, independent CPU inference and numerical gradient checks.
- Native D3D12 FP32 inference on the recorded test configuration, including raw timestamps and separate file-pipeline measurements.
- CPU/GPU pixel agreement at 1440p and on an actual Enfusion capture; random-alpha and dimension checks through 4K.
- Enfusion Lab doctor, isolated addon compile validation and visually inspected Arland capture.
- Three diagnostic scene variants with explicit camera, date, time, weather and wind controls; nine independent captures and all nine pairwise comparisons.
- Telemetry and image-hash checks, dataset-group split validation, unaligned image errors and a bounded integer alignment estimate.
- Twenty-one-page Markdown documentation site with system/light/dark themes, still comparisons and synchronized videos; shared agent/human protocol, Linux CPU CI, Windows build/smoke workflow and GitHub Pages deployment workflow.
- Eighty camera-path samples at 2560 × 1440, each with a GPU output checked against the independent CPU reference. One encoded stream keeps before/after playback synchronized. It is a retimed offline sequence, not live performance.
- Camera projection, exposure, environment and selected engine settings readback checks. Three final static repeats and an earlier probe batch remain documented, including nonzero pixel differences.
- Original material room generated with Blender Cycles, limited-bounce source, multi-bounce reference and independent-seed noise check. Exact source/reference depth and object-ID agreement; scene-linear RGBA and auxiliary EXR passes retained locally. This is synthetic data, not an Enfusion/reference pair.
- Thirty-nine reviewed PNGs and twelve videos with source records, hashes and attribution. Scaling, label bands and compression are recorded for each video/poster; original source/model frame PNGs remain available.
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

The completed local fit is `experiments/local/lighting-diversity-fit-v1/`; CPU model fitting is `experiments/local/lighting-diversity-models-v1/`; regressions are `experiments/local/lighting-diversity-regression-v1/` and `experiments/local/lighting-diversity-regression-v1-videos/`. Portable reports are `evidence/lighting-diversity-fit-v1.json`, `evidence/lighting-diversity-regression-v1.json` and `evidence/lighting-diversity-regression-video-v1.json`. The lighting graph has no native GPU implementation.

Three read-only Workbench resource probes compiled and completed before the test render. `evidence/enfusion-resource-probes-v1.json` records their hashes and counts. Resource names and map locations are available; no live neural bridge was proven. The `ENR_ImageBridge.c` and optional entity-placement scripts passed silent ScriptEditor validation in run `20260909T055234-51d147e1ad`, without loading a world. `evidence/enfusion-image-bridge-compile-v1.json` records the actual script hashes. Three texture-copy runtime attempts are terminal: two timed out and the third crashed after making the widget visible. `evidence/enfusion-image-bridge-v1.json` retains their failures; none proves image return. The external CPU controls and verifier tests pass, including rejection of a one-channel pixel error, a failed widget under a successful capture, and altered evidence. The copied-texture route has failed under three scheduling variants. Test a separate file-return route only with an explicit new hypothesis and preserve its outcome. Summarize each run with `scripts/summarize_enfusion_image_bridge.py`; exact UI pixels cannot certify a scene render pass. A successful screenshot/UI roundtrip would still leave the lighting model's scene buffers and presentation contract unresolved.

The active goal also requires varied actual Arma tests, including cities, interiors, vegetation, vehicles, characters and objects. Reviewed source scouts now cover Everon town streets, a warehouse interior, vegetation, a factory and placed vehicle/character entities. Neural fidelity on these environments, aligned appearance targets and supported integration remain required; source captures and synthetic results cannot close them.

The raw identity attempt in `experiments/local/image-bridge-identity-v1/` is also terminal. It timed out before its raw screenshot callback, leaving no source PNG or CPU output. The runtime evidence includes this fourth failure. The CPU suite has 48 tests; the documentation contains 21 pages, 39 PNGs and 12 videos. Check current CI for the tested revision.

Prepared local scout configs are under `experiments/local/arma-diversity-scouts-v1/` for Beauregard, Arleville, a harbour and an initial Everon overview. Their camera framing is unverified, and Arland towns do not replace the required larger city test. The image probe accepts `--config` and optional `--entities` for a vehicle/rifleman placement test using resource names found by the inventory. The corrected placement script has now spawned an upright M998 and standing rifleman in Saint-Philippe; both are visually verified in the source scene. The probe loader requires `--world-inventory` to bind an additional world to a completed native inventory; the default sequence contract still restricts callers to Arland.

A search-only inventory now completes with normal ScriptEditor initialization and no world load. It observed eight world resources, including `{853E92315D1D9EFE}worlds/Eden/Eden.ent`. Raw evidence is under `experiments/local/resource-inventory-module-v2/`; the portable report is `evidence/enfusion-world-inventory-v1.json`. Two silent attempts and one earlier normal-startup timeout remain retained. The additional-world loader verifies this distinct operation's manifests, scripts, natural exit and callback/search completion. The CPU suite includes rejection of changed manifests, incomplete callbacks and a native capture failure accompanied by otherwise valid image files.

Everon loads in the WorldEditor search-only probe. `evidence/enfusion-everon-scout-v1.json` records the initial coast-and-sky overview and an earlier material-traversal timeout. The revised query completed with 170 named locations among 650 descriptors. `scripts/capture_enfusion_scout.py` then captured ground-level sources at observed locations. `evidence/enfusion-arma-scenes-v1.json` retains the Saint-Philippe garden, two failed entity placements, corrected upright placement, four factory views, four interior views and four Montignac street views. All were visually inspected. Warehouse and street views contain unsupported-looking objects; their cause remains unverified. Do not accept those captures as appearance references or infer neural behavior from them.

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

All listed render, evaluation, bridge and scout jobs are terminal. Do not restart the frozen synthetic evaluation or repeat failed callbacks without a new supported hypothesis. The current real-scene work is on `experiment/arma-scene-return`; reviewed source PNGs are byte-for-byte copies with manifest hashes. Raw runs remain ignored.

Immediate next acceptance: identify an authoritative supported renderer extension and verify identity/inversion at its intended stage, followed by the lighting feature mapping. Separately, diagnose the source visibility anomalies through single-variable repeats, then add short real-scene motion paths and aligned engine/reference lighting pairs. Native lighting execution and complete-frame timings follow a valid input/output contract. See the [roadmap](roadmap.md) for the full unfinished goal.
