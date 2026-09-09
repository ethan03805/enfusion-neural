# Decisions

## 001 · Fidelity before throughput

Accepted 8 September 2026. The target is photorealism that preserves scene identity, with 1440p/20 FPS as the local playable floor. This supersedes the earlier provisional 60 FPS reconstruction-first direction. Fifty milliseconds is the full-frame budget. Other resolutions remain required.

## 002 · Keep the first neural graph small

Accepted for the bootstrap milestone. A 251-parameter CNN makes gradient checks, CPU/GPU parity and complete inspection practical. It trains all layers from original procedural fixtures and runs through native D3D12. Its reconstruction task is a reference problem, not the final fidelity model.

## 003 · Separate offline evidence from integration

Accepted. Enfusion Lab provides editor capture and compile validation. No demonstrated native resource bridge exists in this project. Workbench screenshots do not prove motion-vector access, linear scene color, runtime presentation or Workshop distribution.

## 004 · Native fixed-graph backend first

Accepted for v0. Reuse the installed Windows graphics toolchain rather than introducing a large ML stack for 251 parameters. Specialize weights at startup and report compilation cost separately. This trades generality for auditability. Evaluate WinML/ONNX Runtime when the appearance graph grows; record operator partitioning and avoid hidden CPU fallback.

Current ONNX Runtime documentation places DirectML in sustained engineering and points new Windows feature development toward WinML. That informs a future runtime evaluation, not a requirement to rewrite the small HLSL reference. See [sources](sources.md).

## 005 · Portable documentation in the code repository

Accepted. Markdown is canonical. A small static build creates GitHub Pages with shared navigation, responsive typography and no client framework. AGENTS.md is the shared engineering protocol; CLAUDE.md links to it. Keep game captures and machine profiles local, with reviewed numerical evidence in Git.

## 006 · Begin with measured scene repeatability

Accepted 8 September 2026. The first scene pack uses three explicit camera/lighting variants in the installed Arland world. It controls and verifies date, time, weather and wind through a project-owned extension of Enfusion Lab's adapter. It keeps the plugin's process ownership and capture checks. The installed plugin is unchanged.

The views overlap and remain one diagnostic group. A repeated scene is not automatically a training target or a new independent test scene. Render scale, FSR, quality preset and projection remain null until verified. Nonzero image differences are retained rather than corrected away.

## 007 · Documentation presentation

Accepted 8 September 2026. Remove the logo and promotional copy from the site, keep personal computer specifications out of rendered documentation, and provide a system/light/dark theme preference. Preserve hardware details in raw benchmark records so measurement provenance is not lost.

## 008 · Publish traceable visual comparisons

Accepted 8 September 2026 at the user's request. Publish the existing Arland benchmark pair and the first capture from each reference scene variant. Keep image bytes unchanged, record provenance in the media manifest and check their hashes during the site build. These screenshots are outside the MIT code license; include game attribution and the content usage policy.

Show the model's visible failures alongside its numerical results. Use a manual comparison slider with a static fallback. Independent still captures are not a motion sequence; publish before-and-after video only when source and output frames can be synchronized and playback conditions documented.

## 009 · Sample motion with an explicit offline time convention

Accepted 8 September 2026. Capture numbered frames along one fixed path, hold the camera before each request, and pair each input with exactly one verified GPU output. Encode both sides in a single stream. Keep simulation time, capture/export behavior, processing time and playback rate separate. Retiming is allowed for the documented diagnostic clip; it is never a real-time performance result.

## 010 · Separate stored settings from viewport verification

Accepted. Start Workbench with isolated editor, engine and diagnostic settings files. Validate actual camera projection, exposure, environment, exported dimensions and engine setting readback. Do not infer main-viewport scale or FSR from workspace settings or startup preview dimensions. The current capture contract leaves those fields unverified until a positive control succeeds.

Follow-up probes confirm diagnostic-file loading, but neither diagnostic resolution presets nor workspace controls establish the main viewport's behavior. The workspace changes dimensions after startup, so readback timing must be explicit. The separate render-target callback rejects export. Preserve these negative results and keep the existing capture contract unchanged; see [the investigation](capture-controls.md#diagnostic-investigation).

## 011 · Original path-traced reference data

Accepted. Generate one original room from shared JSON geometry, camera, light and material constants. Compare a limited-bounce source with a multi-bounce Cycles reference, retain linear EXR passes, and measure a second reference seed. Exact depth/object-ID agreement and a noise threshold are initial data checks. Synthetic source renders remain distinct from Enfusion source renders; an engine/reference pair requires a separate import and calibration check.

## 012 · Isolate diffuse-light reconstruction before asset scaling

Accepted at the user's request. Hold resolution, sample count, geometry, materials and other transport settings fixed while reducing diffuse-bounce depth. Fit a compact scene-conditioned model, an RGB-only ablation and a simple affine baseline. Keep train, validation and test view/light combinations explicit within one diagnostic scene group. Use additional reference seeds to reveal correlated sampling noise; publish a preselected ordinary test and out-of-range case.

The resulting lighting graph is independent of the v0 D3D12 bootstrap. It has a versioned CPU model contract, not a live runtime. Investigate retained surface/material representations and a supported Enfusion bridge before collecting all-game assets. Photographs require correspondence and illumination separation to become faithful targets. See [lighting results](lighting-study.md) and [technical feasibility](feasibility.md).

## 013 · Freeze models before scene-transfer and motion evaluation

Accepted 9 September 2026. Commit the path, new geometric layout, model hashes and publication frame before rendering. Evaluate the existing models without training on the new sequences. Produce an independent reference at every frame and measure changes in reconstruction error on matched static surfaces. Preserve boundary, unmatched-region and marking-contrast metrics rather than inferring fidelity from whole-image averages.

The [result](lighting-motion.md) narrows the claim: average error improves, but the scene-conditioned model loses to RGB-only on the new layout and worsens marking contrast. Tiny mean temporal differences do not establish perceptual stability. The next model experiment needs scene diversity, a further untouched test scene and explicit input/contrast checks; the published paths become regression data.

## 014 · Separate layout selection from final evaluation

Accepted 9 September 2026. Declare four training layouts, one validation layout and one untouched test layout before rendering. Compare full scene inputs, no absolute world position and RGB-only with identical sampled pixels and optimizer steps. Input-layer capacities differ explicitly. Select checkpoints and the candidate using validation only, then commit a lock before test rendering. Keep both published paths and old models as regression controls.

Require source and affine-baseline improvement, source-relative boundary/post and marking-contrast limits, temporal non-regression and a reference-seed sensitivity check. Render all test roles at 8,192 samples and publish complete clips and failures. Current regression results improve the partitioned scene but do not replace the untouched test or the independent Enfusion integration requirement.

The completed untouched test passes for the validation-selected full-input model and the relative-input variant. RGB-only fails aggregate spatial and temporal checks. Keep the original selection and thresholds; the result does not authorize choosing models retrospectively by scene. All three complete clips and the old regression paths remain available. The supported engine bridge and varied actual Arma coverage are separate unfinished requirements.

## 015 · Publish completed tests while keeping integration unresolved

Accepted 9 September 2026. Publish the complete untouched synthetic test and all controls with their failures. Do not hold finished evidence behind an unproven engine interface. Keep the full goal active: supported scene inputs/output and varied real Arma coverage remain required. Record runtime failures separately from compilation, and separate source-only environment scouts from neural integration tests. A native crash cannot become a successful proof because a later screenshot exists.

## 016 · Preserve source and presentation failures

Accepted 9 September 2026. The ordinary screenshot route exports RGB8. Accept it only through an explicit file-source contract that preserves RGB values and records supplied opaque alpha. Keep strict RGBA validation elsewhere. A correct CPU file and successful widget load do not satisfy texture readback or presentation verification.

Publish reviewed real-scene captures with exact source bytes, including source visibility anomalies and failed entity placements. They remain source observations, with no aligned appearance target or lighting-model result. Resolve those anomalies and the supported rendering interface before treating broader asset collection as training progress.
