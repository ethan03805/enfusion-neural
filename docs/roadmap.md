# Roadmap

The following stages define the implementation and evaluation work. Each must produce inspectable evidence before a stronger claim is made.

## 01 · Neural foundation

Train a small network, execute it on the recorded test configuration, compare every pixel with an independent reference and retain raw timings. Provide an engine-independent core, reproducible commands, CI and documentation. This repository begins here; see [evidence](evidence.md) for measured scope.

## 02 · Reference scenes and appearance data

**In progress.** The first pack defines three diagnostic Arland views with explicit camera, date, time, weather and wind controls. It supports three independent repeats per scene and image-difference analysis. See [reference scenes](reference-scenes.md) for the exact scope and unverified settings.

The newer [capture adapter](capture-controls.md) verifies projection, fixed exposure, environment, output size and engine settings readback. Internal viewport scale and FSR still need a positive control. Three final repeats retain measurable variation, especially in foliage.

An 80-frame path and [synchronized before/after video](comparisons.md#motion) are implemented. The [material room](material-room.md) provides an original synthetic pair with exact depth/object-ID alignment and a measured reference noise check. Neither milestone establishes a live engine renderer or a valid Enfusion appearance-training pair.

Next: close the viewport settings gap, isolate residual temporal variation, and import the controlled geometry into Enfusion. Verify source/reference camera, light, material and color conventions before training on engine pairs. Add exposure transitions and separate scene families for held-out evaluation.

Acceptance: a versioned scene/config manifest; three repeat captures with measured alignment/drift; separate train/validation/test scene groups; a documented method for producing aligned appearance targets. Captures without a valid target can measure stability and appearance, but must not be relabeled as supervised photorealistic ground truth.

## 03 · Supported integration contract

**Parallel research track, no assumed bridge.** Locate an authoritative rendering extension and prove identity/inversion at the intended stage. Establish color, resource ownership, fences and presentation. Validate each optional buffer independently. If only an external viewer is feasible, name its limitations and measure latency before selecting it as a product route.

Acceptance: a minimal reproducible adapter and a verified available/missing field table. Without this, keep experiments offline. This track can invalidate a proposed product route before expensive training.

## 04 · Faithful appearance model

Train a compact deterministic model on the accepted paired references. Begin with constrained lighting/material correction, preserve detail and assess whether the available inputs support the effect. Compare with identity, the v0 reference and simpler non-neural correction. Introduce temporal information only after motion/exposure validation.

Acceptance: blinded visual improvement with geometry, identity, visibility and temporal checks passing on held-out scenes. Publish failures. More parameters or an appealing single frame do not satisfy this gate.

## 05 · Playable local demonstration

Integrate the accepted model and measure the complete application at 1440p. Preserve a disabled path and rapid fallback. Characterize multiple resolutions and quality profiles. Run the full frame-time and soak protocol.

Acceptance: at least 20 FPS with acceptable pacing on the recorded test configuration, no fidelity regressions in the test suite and recorded memory headroom. The exact performance result must identify scene and settings.

## 06 · Scale training only when justified

Before renting hardware, measure local training throughput and memory, estimate dataset and experiment size, and provide a concrete cost/time plan. Use a portable model interchange and resumable checkpoints. No paid resource has been provisioned. Hardware rental requires a separate authorized budget.

Training may move to a larger GPU; inference must still be validated on the test hardware. Additional Enfusion titles and other GPUs each require their own adapter and evidence.
