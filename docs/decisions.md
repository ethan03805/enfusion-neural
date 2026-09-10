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

## 027 · Reject stronger RGB models when identity or useful appearance fails

Accepted 10 September 2026. Evaluate the pinned REGEN GTA2Cityscapes generator on three preselected gameplay frames before live integration. Its RX 7800 XT DirectML output matches the independent CPU result, but the 53–54 ms synchronized call at 960 × 544 is too costly and changes roof identity, sky texture and fine detail. Retain the complete model/export/profiling record and close that integration attempt.

DeepLPF's local photographic filters retain broad colors but clip shaded visibility. A declared source-protection diagnostic prevents new black clipping and preserves dark source pixels, yet gives only color/contrast adjustment. Do not spend further GPU conversion work or call that substantial photorealism. Preserve the native exposure companion, publish concise reviewed comparisons, and require an identity-linked appearance reference before another broad model integration. Candidate code and weights keep their author's separate licenses; rejected weights are outside the playable package.

## 028 · Separate sustained operation from sustained movement

Accepted 10 September 2026. Extend the owned benchmark session to 600 seconds while retaining its original 30–60 second walk/turn segment. The remaining camera is stationary. Report the complete session and every minute, retain all stalls and capture-internal event exclusions, and do not treat this as manual gameplay or motion-fidelity acceptance. The run completes 36,654 processed frames without a crash or recorded hide/timeout, with one interval above 50 ms. The unchanged pipeline and download remain available while the appearance objective stays unfinished.

## 029 · Require motion and repeatability before adding a gameplay path

Accepted 10 September 2026. Reject the second fence-colliding pilot, survey the actual town with Enfusion Lab and use the adjacent tree-lined street. Validate the isolated addon before launching. Require at least 50 metres of walking displacement, at least 1 m/s at interior one-second samples, and at most 0.5 metres of camera separation from the standard pass. The three completed passes travel 73.9–74.2 metres and meet those gates. Label coverage as street vegetation edges, not dense forest or semantic visibility acceptance.

Preserve the first street launch's world-loading crash and the first complete standard pass's 295 ms presentation stall. Keep all 34 seconds at original speed and report recording overhead. Path acceptance does not establish substantial neural appearance improvement, physical input or displayed-frame latency.

## 030 · Close the empty DXGI display-counter route after two probes

Accepted 10 September 2026. Add optional `GetLastPresentCount`/`GetFrameStatistics` logging after Present, retaining raw HRESULTs and all counters. The first street run returns one initial disjoint result followed by 2,922 successful calls with all display counters zero. The single declared `DwmFlush` follow-up also returns zero counters across 2,918 successful calls, while adding synchronization cost. Submitted-present IDs advance but do not establish display timing.

Stop this route. Keep the optional diagnostic implementation, raw traces and original non-probe binary. Leave flags off by default, retain the unchanged download and earlier separate software display join, and continue to label moving-path display and physical latency unavailable. The neural GPU shader remains byte-for-byte unchanged and the rebuilt native curve matches its independent CPU reference within 0.000000075.

## 031 · Identify a real gameplay material before proposing its correction

Accepted 10 September 2026. Inspect the accepted street location through supported read-only Workbench APIs. Preserve the first 160-object inspection limit and the initial unresolved slot handles. Native inventory resolves three unique roof/wall material names from the observed `House_Village_E_1L02t` mesh; their `MatPBRMulti` containers expose slate, plaster, brick and mask references. Retain both full survey images and all validation/inventory/schema hashes.

Do not equate matching asset-folder/slot names with verified per-instance overrides, or native texture references with decoded pixels and photorealistic ground truth. No game asset is modified or source texture published. The next appearance step verifies the actual binding and texture inputs before choosing a correction target; the working companion remains unchanged.

## 032 · Close native texture access and test RGB detail restoration

Accepted 10 September 2026. Read the observed house's native prefab: its MeshObject exposes all 13 default material assignments, including the three previously identified roof/wall containers. The Materials object array is empty and EntityToSource returns null in simulation. Preserve the distinction between explicit defaults and unverified active overrides.

The one declared VFS file-access probe enters its callback, then times out before its first per-file result. No bytes are copied. The logs do not isolate which file operation stalled; subsequent files are untested, not absent. Preserve the failed run and stop this route at its bound. Official packed-channel documentation does not substitute for decoded pixel validation or an aligned improved target.

Use the existing RGB contract for a bounded restoration-model evaluation. Require a useful detail result, source identity controls and measured RX 7800 XT cost before integration. Reconstruction from synthetic downsampling can establish restoration accuracy only; it does not demonstrate photorealistic relighting or complete the appearance objective.

## 033 · Reject costly restoration and verify geometry before lighting correction

Accepted 10 September 2026. SPAN's pinned x2/48-channel EMA checkpoint reconstructs four downsampled gameplay controls more accurately than bicubic. One-time convolution fusion exactly matches its CPU reference; DirectML FP32 and FP16 pass their declared parity limits. Preserve the initial FP16 topological-order export failure and the corrected, reordered graph. Both precision variants exceed the provisional 20 ms call budget, even with the game stopped.

The declared bounded residual produces slight sharpening and some newly clipped channels, with no demonstrated material-response or lighting improvement. Close live integration of this graph. Do not spend motion or application trials on an already over-budget appearance result, and do not present synthetic restoration accuracy as photorealism.

The supported world API exposes collision traces. Test a small grid at the known street house before any new model or companion input bridge. Returned collision geometry may disagree with rendered foliage, openings and visual detail; require projected alignment, coverage and cost evidence before treating it as useful lighting information. This does not reopen the exhausted renderer-resource or screenshot/widget routes.

## 034 · Keep collision sampling offline and test native material controls

Accepted 10 September 2026. The declared 64 × 36 ray grid completes in both street views after repairing one compile-name collision. Preserve the first float-coordinate projection failure; an explicit integer-coordinate amendment passes the second view's 0.5-pixel control. Plain entity/terrain hits have unit normals, while adding VISIBILITY produces 20 / 25 zero-normal hits. Broad geometry is recognizable, but thin cover, foliage gaps and openings are not validated.

The grid costs 16–25 ms on the CPU before any model or bridge. Close its per-frame integration and retain the working offline probe, all three validations and both captures. Do not substitute collision results for shading buffers or imply that all sparse/offline queries are infeasible.

The native Material API independently documents cached lookup, parameter assignment and reset. A bounded source/change/reset experiment on the already identified roof can test an appearance control without copying textures. Modify only a declared in-memory scalar in a private process; preserve the native asset and texture identity. Require visible response and restoration before any reference or model claim. No correction target has yet been established.

## 035 · Use the verified material control without overstating its appearance result

Accepted 10 September 2026. One private source/change/reset sequence loads the cached roof material, assigns `RoughnessScale=0.05` and resets it. Parameter index 74 and assignment success are accompanied by a visible roof response, not used as sufficient evidence alone. All declared image gates pass: roof change 26.1407 codes, reset 0.0403, sky change 0.0085. Full-frame reset is not exact; retain its 178-code maximum and all unchanged PNGs.

This proves a native in-memory material control while preserving texture references and geometry. It does not establish a realistic target, per-instance isolation, surface-buffer access or neural enhancement. Compare moderate candidate values against documented slate references and a reserved view before preparing any optional material preset. Report native material and neural RGB contributions separately in subsequent gameplay comparisons.

## 036 · Reject material candidates when appearance fails despite clean controls

Accepted 10 September 2026. Compare only roughness multipliers 0.4 and 0.7 at three declared views with fixed environment and camera. Inspect two manufacturer slate references without redistributing them or inferring calibrated roughness. Reject 0.4 in the selection views; record 0.7 as the sole candidate before the reserved sequence. Its broad pale response reduces weathered slate contrast in that view, so reject it as well. No newly clipped channels and successful reset do not establish a visual benefit.

Keep the original material, working native control, all twelve captures and pre-selection hashes. Do not train against these candidates or add a preset to the playable download. The next neural investigation evaluates relative depth inferred from available RGB, using existing collision samples only as limited offline checks. This preserves the source-coordinate contract and does not imply renderer depth access or accept a new lighting effect before evidence.

## 037 · Distinguish coarse RGB depth from usable surface geometry

Accepted 10 September 2026. The two declared Depth Anything V2 Small FP32 graphs complete on RX 7800 XT without CPU execution fallback and pass independent CPU parity. Actual input shapes are 462 × 252 and 714 × 392. The smaller graph's 10.21 / 10.98 ms medians pass the provisional 15 ms p95 model-call ceiling; the larger graph's approximately 24 ms calls fail. The single FP16 graph fails session creation because operations were assigned to CPU with fallback disabled. Preserve it without claiming FP16 timing or diagnosing a specific unsupported operation from the error alone.

Both FP32 outputs pass the predeclared combined street geometry gate after an even-grid affine inverse-depth fit. Keep the weaker building-only results visible: reserved ordering 0.798 / 0.722, versus approximately 0.997 on ground. The closeup projection failure excludes it from numerical geometry acceptance. Flattened openings, incomplete roof fittings and smooth foliage prevent using these estimates as surface normals or per-pixel relighting geometry.

Close the bounded investigation after 17.4 minutes. Retain the smaller graph for a separate motion/HUD feasibility check as a coarse auxiliary input; do not accept a lighting effect or change the runnable package. Any next test must use a fixed time-limited gameplay segment, original timestamps, fixed normalization and a reserved segment without retuning. Appearance gain and complete application performance remain independent acceptance gates.

## 038 · Close the depth motion diagnostic without claiming a lighting result

Accepted 10 September 2026. Process all 600 frames of the declared ten-second walking/turning segment, keeping the final three seconds reserved. The new 448 × 252 FP32 graph passes independent CPU parity and records only DirectML execution events. Preserve every input hash, raw prediction, timing and source presentation timestamp. The encoded comparison retains all relative timestamps to numerical roundoff and uses the first prediction's grayscale range throughout.

The coarse correspondence diagnostic passes on both splits, with 80.45% median reserved coverage. Actual camera-relative depth changes and imperfect flow prevent interpreting this as pure flicker or semantic geometry acceptance. Broad surfaces persist; flattened openings and softened thin cover prevent surface relighting. All contact sheets and four native-size key pairs were inspected, but the planned entire-clip real-time playback review remains incomplete. Record this deviation explicitly.

The 14.93 ms median / 15.88 ms p95 model call fails the provisional 15 ms p95 limit. Author CPU preprocessing adds 30.16 ms median. Close this workflow for live integration and close the investigation after 17.7 minutes. Keep the working package unchanged. Establish a useful, aligned appearance target before optimizing depth or adding another learned effect; neither a depth map nor a clean numerical result meets the photorealism objective.

## 039 · Reject a native illumination assignment without a useful image response

Accepted 10 September 2026. Read the active world's sky material and two relevant entities within a declared 5,000-ID prefix. Retain the reached scan limit, prefab/resource versus active-state distinction and absent simulation instance source. The native atmosphere exposes `SkyIntensityLV=8`; choose only 8.5 before changed capture. Both isolated addons validate, and the fixed-camera source/change/reset sequence completes with assignment success at parameter index 83.

No useful lighting response is visible. Roof change is 0.0424 codes versus 0.0353 for reset, sky change is 0.000144 codes, and reported HDR exposure is unchanged. Keep the 190-code changed and 206-code reset full-image maxima. Do not infer an ignored parameter, weather overwrite or cached-atmosphere update mechanism from this evidence alone. Reject in the selection view and leave the reserved view unused. Close the investigation after 12.8 minutes with the working code and every capture retained.

There is still no aligned improved native target. Return to the verified RGB input contract for one bounded evaluation of a compact pretrained local/global correction model, IAT. Its author parameter count and timing do not establish local feasibility. Require source fidelity, visible benefit and actual RX 7800 XT measurements before any motion or live integration work; do not accept another generic brightness change as completion of the appearance objective.

## 040 · Reject IAT without optimizing away its appearance failure

Accepted 10 September 2026. The pinned exposure checkpoint executes unchanged at 960 × 540 on RX 7800 XT DirectML FP32 and passes all CPU comparisons. Synchronized calls include upload and readback of all three author tensors; 37 calls generate 1,517 DirectML node events with no CPU execution. Per-view p95 is 28.99 / 29.87 / 30.18 ms, failing the declared 10 ms ceiling.

Record rejection on the two selection views before opening the reserved foliage image. Raw outputs oversaturate sky/vegetation and lose shaded detail. The fixed bounded residual caps changes at ten RGB8 codes but adds insufficient appearance benefit, newly clipped channels and visible hard HUD-mask seams. Preserve the diagnostic defects rather than retune after selection. The live DCE compositor uses feathered margins and remains unchanged. No alternate export, FP16, motion, training or live integration follows this failed appearance result. Close the evaluation after 14.1 minutes.

Stop the generic photo-grade sequence. The missing aligned target and demonstrated material/lighting gain remain explicit. Complete the independent sustained-movement acceptance gap next with a bounded matched-route run; do not describe runtime progress as completion of the photorealism objective.

## 041 · Accept sustained route evidence with explicit review and timing limits

Accepted 10 September 2026. The fixed 42-second out-and-back cycle gives each final 180-second pass 156 moving seconds and 590–591 metres of travel. All motion gates pass; maximum camera/direction difference is 0.78 m / 1.46°. Preserve the first sparse-log direction failure. One measurement amendment increases logging to 10 Hz without changing route or thresholds; decimation demonstrates that sparse interpolation alone can produce a 14.43° turn error, without proving the cause of every earlier difference.

The first enhancement attempt processes zero frames and has no video. A later old crash reporter is closed locally without submission; the intervened standard pass is excluded because of UI intervention. Add foreground logging and startup checks for game focus and companion frame evidence. The final three passes retain game focus and the companion processes 11,925 frames over its 198-second session with no recorded hide, bypass or timeout. This does not verify physical keyboard/mouse input.

Recorded game rates are 69.99 / 85.72 / 72.03 presents/s. Companion rate is 60.21, with p95 / p99 intervals 30.57 / 32.74 ms and 85 intervals above 33.3 ms. GPU copy/network/draw is 3.53 / 6.28 ms median/p95; capture-to-Present age is 6.58 / 14.14 ms, retaining the negative clock-skew minimum. No moving display or physical input latency is inferred. Keep recording gaps and encoding overhead separate.

Review all 552 one-second samples, 24 native keys and the composite poster. Source identity is recognizable; the effect remains a modest brightness change, with blur and aliasing unresolved. Continuous real-time perceptual review and full temporal acceptance remain incomplete. Slow CPU extraction is stopped with partial artifacts retained; GPU-assisted extraction completes. Its standard timestamps and contact sheets exactly match the CPU results, while native decoded key colors differ slightly and both sets are retained. Gameplay finishes within the hour; review/evidence closes at 66.0 minutes, explicitly over the original bound. Do not reset that clock or run more trials under the plan.

Keep the working download unchanged. Close repeated baseline measurement for this route until a processing change warrants another comparison. The missing appearance target is next: one bounded source-conditioned synthetic proposal, fixed landmarks and strict identity/visibility review. Treat it as art direction only, reject invented detail or geometry, and do not use a failed target for training. Prompt-driven per-frame redraw remains outside the live architecture.

## 042 · Reject reconstructed detail in an offline synthetic target

Accepted 10 September 2026. Freeze one 2560 × 1440 street source, the exact prompt and eleven landmark regions before one built-in image-tool call. The returned 1672 × 941 proposal makes roof, plaster and road shading stronger, but reconstructs fine roof/asphalt texture, foliage and painted lettering. Broad scene resemblance is insufficient for the identity contract. Exact openings, thin cover, shadow boundaries and shaded target visibility remain uncertified.

Inspect both complete originals and every frozen region. Reject the target and retain the unchanged tool PNG, including its provenance metadata, without resizing, alignment, cleanup or a second candidate. The 3.5-minute check stays within the 20-minute bound. It is synthetic art direction, not photographic ground truth; no training or live integration follows. Remote tool response time establishes nothing about RX 7800 XT performance. The runnable build is unchanged.

Close this proposal route. The aligned target and substantial appearance gain remain unresolved. Address the independent temporal gap next using paired source/enhancement frames and source-only correspondence, retaining the diagnostic's exclusions and limits. Runtime or temporal progress must not be reported as solving the appearance blocker.

## 043 · Retain CPU composition failure and measure the exact native pass

Accepted 10 September 2026. The independent CPU network matches the saved native snapshot within 1.79 × 10⁻⁷, but full RGB8 composition fails its frozen mean-error gate: 0.033434 codes versus 0.02, with a one-code maximum. Stop that route before temporal processing. Preserve its mostly positive discrepancy without assigning an unproved cause or loosening the gate.

One offscreen D3D11 alternative uses the existing network, exact extracted shader and RX 7800 XT. It reproduces every saved curve and output channel exactly and retains the independent CPU network check. Keep the original source, 600 timestamps, strength, split, thresholds and deadline. Complete the same-frame exposure diagnostic with source-only flow; both splits pass the coarse gates, identity is exactly zero and alternating brightness fails as intended. Reserved coverage is 83.79% of the declared screen region. These exclusions prevent full temporal or semantic acceptance.

Retain the separate color-preservation failure: 51,129 newly endpoint-clipped channel samples across 600 frames, maximum 290 per frame. Luminance protection and a bounded RGB delta do not guarantee channel headroom. The four fixed keys contain new white endpoints; the aggregate combines both endpoints. Review all ten chronological contact samples and four complete native-size key pairs. Source structure persists with modest midtone changes, unresolved blur/aliasing and no accepted photorealistic gain. Full real-time perceptual review remains incomplete.

Close measurement/review/evidence after 18.0 minutes, within the original 30-minute bound. Publish the entire ten-second comparison with all relative timestamps unchanged. Offline upload, curve dumps and readback establish neither live frame rate nor added latency. The live shader and runnable package are unchanged. Correct channel saturation next using a bounded source-preserving guard, then require separate live verification before replacing the download; preserve this original output as the failed control.
