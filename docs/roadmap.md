# Roadmap

The following stages define the implementation and evaluation work. Each must produce inspectable evidence before a stronger claim is made.

**Immediate next task:** identify a supported Enfusion entry point and minimal example that can satisfy the [feature and execution requirements](integration.md#feature-and-execution-requirements). The [interface audit](integration.md#interface-audit) has not established one. The native graph passes all numerical controls and all 112 retained CPU comparisons, but input semantics, resource ownership, output placement and synchronization remain unresolved. Once a concrete route exists, verify the inputs and passthrough/change/bypass controls before connecting the graph. Actual Arma model/reference coverage and complete-frame performance remain required before this goal is complete.

Further color-lookup calibration can answer bounded color/sampling questions, but cannot supply the full model's surface inputs. Do not treat more training, an RGB-only lookup or another unchanged screenshot/widget retry as progress on that missing interface. The prepared Bohemia inquiry remains unsent pending the existing authorization request; no contact has occurred.

The [point-light calibration](light-calibration.md) is complete and fails seven of 22 reserved response checks. All eight native captures, four reference passes, unchanged fit coefficients and failures are retained. Before accepting an appearance-training pair, separately isolate environment/reflection contributions and verify color/material response on independent controls. Do not rerun the same fit, select a new curve on reserved data or loosen its thresholds. The original area-light fixture and locked models remain unchanged.

## 01 · Neural foundation

Train a small network, execute it on the recorded test configuration, compare every pixel with an independent reference and retain raw timings. Provide an engine-independent core, reproducible commands, CI and documentation. This repository begins here; see [evidence](evidence.md) for measured scope.

## 02 · Reference scenes and appearance data

**In progress.** The first pack defines three diagnostic Arland views with explicit camera, date, time, weather and wind controls. It supports three independent repeats per scene and image-difference analysis. See [reference scenes](reference-scenes.md) for the exact scope and unverified settings.

The newer [capture adapter](capture-controls.md) verifies projection, fixed exposure, environment, output size and engine settings readback. Internal viewport scale and FSR still need a positive control. Three final repeats retain measurable variation, especially in foliage.

An 80-frame path and [synchronized before/after video](comparisons.md#motion) are implemented. The [material room](material-room.md) provides an original synthetic pair with exact depth/object-ID alignment and a measured reference noise check. Neither milestone establishes a live engine renderer or a valid Enfusion appearance-training pair.

Next: close the viewport settings gap, isolate residual temporal variation, and calibrate the imported controlled geometry in Enfusion. Verify source/reference light, material, shading and color conventions before training on engine pairs. Add exposure transitions and separate scene families for held-out evaluation.

Acceptance: a versioned scene/config manifest; three repeat captures with measured alignment/drift; separate train/validation/test scene groups; a documented method for producing aligned appearance targets. Captures without a valid target can measure stability and appearance, but must not be relabeled as supervised photorealistic ground truth.

## 03 · Supported integration contract

**Parallel research track, no assumed bridge.** Locate an authoritative rendering extension and prove identity/inversion at the intended stage. Establish color, resource ownership, fences and presentation. Validate each optional buffer independently. If only an external viewer is feasible, name its limitations and measure latency before selecting it as a product route.

Acceptance: a minimal reproducible adapter and a verified available/missing field table. Without this, keep experiments offline. This track can invalidate a proposed product route before expensive training.

The [installed-SDK review](feasibility.md) confirms documented material/resource workflows but establishes no native neural processing bridge. It also evaluates asset-specific features and photographic reference data. A complete asset inventory and all-asset training are not implemented.

## 04 · Faithful appearance model

**Initial synthetic diagnostic completed.** The [lighting study](lighting-study.md) changes only diffuse-bounce depth and trains a small scene-conditioned model with RGB-only and affine controls. Held-out camera/light combinations improve, including an independently seeded reference check. The same room/assets appear in every split; temporal behavior and independent scene-family generalization remain open. Six reviewed PNGs show an ordinary test and an out-of-range stress case. No GPU or game-frame performance claim follows.

Train a compact deterministic model on the accepted paired references. Begin with constrained lighting/material correction, preserve detail and assess whether the available inputs support the effect. Compare with identity, the v0 reference and simpler non-neural correction. Introduce temporal information only after motion/exposure validation.

Acceptance: blinded visual improvement with geometry, identity, visibility and temporal checks passing on held-out scenes. Publish failures. More parameters or an appealing single frame do not satisfy this gate.

The [scene-transfer and motion test](lighting-motion.md) evaluates frozen models on two 32-frame paths, including a new partitioned layout. It retains independent references at every frame and records regional/temporal regressions. Average error improves, but the scene-conditioned model loses its advantage over RGB-only on the new layout and worsens marking contrast. The broad faithful-appearance gate remains open.

The subsequent experiment uses multiple original training layouts, an untouched evaluation scene, a fixed-budget ablation of absolute world position, marking-contrast and boundary checks, and higher-convergence temporal references. The earlier paths remain regression data. Native execution must separately match the CPU lighting reference and measure feature, inference and composition cost.

The [scene-diversity experiment](lighting-diversity.md) has completed four training layouts, one validation layout, three locked feature variants and two affine controls. The validation-selected full-input model and relative-input variant pass the untouched 48-frame cross-courtyard test at the predeclared sample count. RGB-only fails aggregate spatial and temporal checks. All three complete test clips and the existing regression paths are retained. The [native GPU implementation](lighting-gpu.md) now passes numerical checks and all 112 full-model frame comparisons. Next: prove the supported input/output route and test actual Arma city, interior, vegetation and entity scenes. World-resource discovery and standalone GPU parity do not meet that integration criterion.

Current [Arma source captures](arma-scenes.md) cover Saint-Philippe vegetation and entities, a factory yard, a warehouse interior and Montignac streets. All views were inspected. Two placement failures and source visibility anomalies remain recorded. These captures establish environment coverage for scouting; model fidelity on these scenes remains untested.

The immediate priorities are:

1. Establish a supported input/output interface. Require a documented extension and a reproducible identity/inversion control at the intended rendering stage, then verify the lighting model's required surface inputs. The screenshot/widget probes have failed; more training cannot resolve this interface.
2. Use the [tested 120-update hold](arma-scenes.md#capture-settling) as the starting point for the next source fixtures. Ten controlled runs show that a longer per-view hold restores the observed warehouse supports and town surfaces; a longer startup wait alone does not. The exact engine mechanism and behavior on new views remain unverified. Preserve the original failures and inspect each new path.
3. Add short motion paths and an aligned engine/reference lighting pair. Verify exposure, camera, material and light conventions; keep town, interior, foliage and entity scenes separate in evaluation.
4. Connect the verified native lighting graph through the supported adapter, then measure features, synchronization, inference, composition and complete-frame cost. Standalone dispatch p95 is 1.961 ms at 1440p; the separate upload/readback cost and startup do not establish a playable pipeline. Use integrated results to decide whether larger training is warranted.

The [original-room control](material-room.md#engine-import-controls) now imports and visibly renders all 12 meshes. The empty outputs came from requesting editor shutdown before asynchronous rebuilding finished. Three build/load controls, per-vertex comparisons and pitched-camera captures establish geometry progress. The [surface follow-up](material-room.md#surface-controls) verifies face connectivity and material assignments, while retaining failed strict normal/UV precision checks. Native material schema inspection succeeds; parameter semantics remain open.

Next use an asymmetric original texture and controlled light to verify rendered orientation, material response and silhouettes. Map material constants, isolate illumination and verify exposure/color correspondence before accepting an engine/reference pair. TXO decimal-grid observations do not establish compiled shading precision. Keep the existing synthetic references and selected model frozen. Geometry import does not resolve the supported neural input/output interface.

The [Color-only control](material-room.md#material-color-control) now passes native readback and predeclared wall-response checks, with both full images published. Roughness/metalness remain default and the engine environment remains unmatched. The next material acceptance requires original packed-map import, an asymmetric texture orientation check, and verified roughness/metalness response under a controlled light; color assignment alone does not satisfy it.

## 05 · Playable local demonstration

Integrate the accepted model and measure the complete application at 1440p. Preserve a disabled path and rapid fallback. Characterize multiple resolutions and quality profiles. Run the full frame-time and soak protocol.

Acceptance: at least 20 FPS with acceptable pacing on the recorded test configuration, no fidelity regressions in the test suite and recorded memory headroom. The exact performance result must identify scene and settings.

## 06 · Scale training only when justified

Before renting hardware, measure local training throughput and memory, estimate dataset and experiment size, and provide a concrete cost/time plan. Use a portable model interchange and resumable checkpoints. No paid resource has been provisioned. Hardware rental requires a separate authorized budget.

Training may move to a larger GPU; inference must still be validated on the test hardware. Additional Enfusion titles and other GPUs each require their own adapter and evidence.
