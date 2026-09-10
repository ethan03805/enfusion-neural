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

## 017 · Settle each source view before judging its detail

Accepted 9 September 2026. Ten controlled runs show that a 120-update camera hold restores the observed warehouse supports and Montignac surfaces/markings in three independent runs per scene. A 30-second startup wait with the original six-update hold retains incomplete detail. Use the longer per-view hold as a candidate for subsequent offline fixtures and inspect every new view.

Keep the initial single-variable plan separate from the follow-up repeats chosen after seeing its results. Preserve short-hold failures and publish unchanged sample-1 comparisons from the first long-hold runs. Simulation updates are not GPU fences, the precise internal cause remains unverified, and pixel differences between independent sources are not model-fidelity scores. This capture improvement does not close the supported renderer bridge or aligned engine/reference requirements.

## 018 · Separate asynchronous resource building from validation

Accepted 9 September 2026. Workbench rebuild requests return before import completes. Keep the isolated editor alive while observing build completion and retained output, then load the result in a separate process with natural exit. The previous immediate shutdown produced header-only resources that were still loadable. Preserve those failed controls and reject empty material-section telemetry.

The original-room fixture now has per-vertex coordinate checks, expected entity bounds and a visible pitched-camera capture. Treat this as geometry correspondence only. Default engine materials and outdoor lighting do not match the synthetic reference, and successful asset import supplies no neural renderer extension.

## 019 · Preserve surface precision failures and separate schema from semantics

Accepted 9 September 2026. Compare face topology, named material assignments and face-corner data before claiming appearance correspondence. Retain the initial normal/UV failures and their original tolerances. Decimal-grid diagnostics explain a plausible source of small differences but cannot certify the compiled mesh or retroactively pass the check.

Use native read-only container inspection to discover available material fields. A `Color` default or `RoughnessScale` readback does not establish a reference-to-engine material mapping. Validate that mapping with controlled original textures, illumination and raster observations before accepting appearance-training pairs.

## 020 · Freeze calibration and keep a lookup control separate from the lighting model

Accepted 9 September 2026. The point-light display hypothesis is fitted only on three declared intensities and one neutral patch. Commit its two coefficients before reserved numerical checks, retain every failure, and do not change the original fixture or locked model to improve this diagnostic. Seven of 22 reserved checks fail. The one-bounce reference already contains indirect illumination; it cannot isolate direct light.

Investigate the documented color-grading/volume-texture workflow as a bounded integration control, starting with native schema inspection and original identity/known-color textures. A lookup-table approximation would support only a pointwise RGB function. It cannot stand in for the full scene-conditioned model, supply missing buffers or pass the broader integration goal. Model quality, effect placement and complete-frame cost require separate evidence.

## 021 · Separate visible lookup response from color accuracy

Accepted 9 September 2026. Original volume imports retain exact RGBA lattice values. The engine rejects the initial priority 1000; a separately committed priority-19 follow-up visibly applies inversion and constant-color controls. Preserve both batches and the complete native texture readback, including its trailing field. Do not infer successful application from material readback alone.

The constant output differs from the stored RGB8 code values, and all unchanged-scene repeats differ. Record every CPU hypothesis and repeat comparison without fitting a transfer or changing previous limits. Declare new color controls, select the convention and freeze accuracy limits before reserved evaluation. Test dynamic switching and exposure separately. The working lookup cannot replace the full lighting graph, scene inputs or actual-Arma fidelity and complete-frame tests.

## 022 · Verify the full lighting graph independently of the engine bridge

Accepted 9 September 2026. Implement all three locked lighting variants as explicit FP32 native record modes while keeping the original RGBA8 path. The independent CPU model remains unchanged. Verify normalization, hidden layers, reconstruction, exact alpha/fallback and the original residual bound before using the graph in Enfusion. Preserve the observed intrinsic-rounding violation; clamp to the defined bound and rerun numerical controls without loosening tolerances.

Reuse all 112 existing source/reference frames and the original fidelity-gate function. Recompute the selected model's linear-space metrics from native output; keep other controls as their recorded CPU results and omit unmeasured GPU display metrics. Standalone dispatch and transfers are separate measurements, and neither establishes a supported engine integration or complete-frame performance.

When storage limits interrupt numerical tests, preserve measured outputs and failures. Generated inputs can be removed only after exact regeneration with retained recipes and source snapshots. Rendered source passes remain authoritative, while packed transfer buffers are temporary and hash-bound to those inputs. Avoid duplicating native output in a second array format when it can be extracted losslessly.

## 023 · Prove the Windows gameplay loop before choosing the appearance model

Accepted 10 September 2026 under the user’s new playable-companion objective. Use Windows Graphics Capture and a separate GPU companion. RGB including HUD is the available contract; the full Blender model cannot run with absent scene inputs. Do not repeat the exhausted screenshot/widget bridge. Measure capture age and complete game performance before committing to a pretrained model. The active target is now 1440p at 30–60 FPS. Keep the existing GitHub Pages address and collapse previous experiments into research navigation.

## 024 · Verify active configuration and distinguish missing trace channels

Accepted 10 September 2026. The game mounts `profile/` beneath the command-line profile root; read back every varied rendering setting before a benchmark. Preserve the initial default-profile results as configuration failures. Use separate CPU presentation and display/GPU traces because some game presents are unresolved by display tracking. Missing GPU data is unavailable, not zero. Reject event loss and missing CPU traces, and stop only this run's owned ETW sessions during cleanup.

## 025 · Preserve the first RGB neural pass and rejected candidate

Accepted 10 September 2026. Zero-DCE++ provides a small native exposure-curve baseline with independent numerical parity. Preserve source coordinates/chroma, bound changes, protect dark/bright and HUD regions, and expose source on bypass, invalid curves or stale capture. The Image-Adaptive-3DLUT sRGB checkpoint is evaluated separately; its unrestricted output clips foliage shadows and is not accepted. Neither candidate establishes reconstructed materials, scene-linear relighting or photorealism. Publish the actual same-frame outputs and retain separate model licenses.

## 026 · Ship the measured pipeline with explicit acceptance gaps

Accepted 10 September 2026. Publish the tested standalone companion, isolated addon, launcher, exact hashes and separate model terms. C++20 fixes the newer MSVC coroutine build failure; the companion links its C++ runtime statically. Package launch, F8/F9/F10 and numerical parity are verified. This is a working pipeline delivery, not completion of the photorealistic appearance goal.

Count only DXGI non-null application swapchains in PresentMon CPU evidence, and decode both UTF-8 and UTF-16 loss logs. WGC internal events otherwise falsely double output throughput. Preserve missing display channels after one bounded display-only retry. Keep recording overhead separate. Normal-speed comparisons retain source timing and all 34 seconds, with explicit spatial scaling and encoding.

The foliage attempt collides with a fence, and its reduced-only path differs around a tree. Retain it as a collision/visibility check, not a matched moving-path performance acceptance. The town route remains the primary controlled comparison. Physical input, full moving-path display latency and substantial appearance improvement remain open.
