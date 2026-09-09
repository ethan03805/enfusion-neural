# Lighting study v1

Diagnostic scene-conditioned diffuse lighting correction. Trained on one original Cycles room; no game assets, photographs or external model weights. This is separate from `bootstrap-v0` and has no GPU implementation or live engine integration.

| Field | Contract |
| --- | --- |
| Models | `lighting-v1.json` (20 inputs); `lighting-rgb-v1.json` (3 inputs) |
| Graph | Input → 32 ReLU → 32 ReLU → 3 tanh |
| Parameters | 1,827 scene-conditioned; 1,283 RGB-only |
| Output | `max(expm1(log1p(source RGB) + 0.25*tanh(raw)), 0)` |
| Color | Nonnegative scene-linear Rec.709; no upper radiance clamp |
| Inputs | Exact ordered names in JSON and `enr/lighting.py`; material constants come from original scene configuration |
| Normalization | Per-feature training mean and standard deviation; minimum scale 0.05 |
| Training | CPU NumPy float32, Adam, 6,000 steps, batch 1,024, rate 0.001, seed 7 |
| Selection | Minimum validation residual MSE; scene step 5,800, RGB step 6,000 |
| Data | 12 training cases × 8,192 pixels; two validation cases × 8,192 pixels |
| Splits | Same room/asset group; three held-out view/light combinations plus one out-of-range stress case |
| License | MIT; original scene and trained parameters |

Targets differ from inputs only in the configured diffuse-bounce limit. Test/stress targets are excluded from fitting and checkpoint selection. Independent-seed references for two cases expose correlated sampling noise. Background pixels are bypassed using source depth; source alpha is copied. No geometric or semantic fidelity guarantee follows from the bounded residual.

Loading: `model, metadata = enr.lighting.load(path)`. Build the documented source features with `features`, flatten pixels to `[N, 20]`, and pass them to `predict` for a log-radiance residual. The RGB ablation receives only the first three features. Add the residual to `log1p(source RGB)`, invert with `expm1`, clamp negative radiance to zero, and preserve the source background/alpha. Display conversion is separate and explicitly recorded.

The model can encode this room's spatial lighting patterns. No independent scene-family, animated object, texture/marking, offscreen geometry change, new material, temporal path or other resolution has been validated. It must not be presented as general relighting, photographic restoration, an FSR replacement or a Reforger renderer. CPU timing excludes feature construction and I/O; previous v0 GPU timings do not apply.

Read [the study](../docs/lighting-study.md) and [complete evidence](../evidence/lighting-study-v1.json) for metrics, visible limitations and source hashes. Reproduction commands regenerate data and retrain both models. The original diagnostic inputs are retained locally and are not bundled with the weights.
