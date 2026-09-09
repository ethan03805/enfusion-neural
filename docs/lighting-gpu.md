# Lighting GPU

The three locked lighting models now run as native FP32 shaders. All 21 numerical size/variant controls pass, and the full-input model matches the retained CPU evaluation on all 112 test and regression frames. This is a standalone backend; Enfusion scene inputs and in-engine neural execution remain unverified.

## Correctness

The shader performs feature normalization, both 32-unit hidden layers, the bounded log-radiance residual and scene-linear reconstruction. Invalid pixels preserve their original source RGB exactly. Alpha is copied exactly, including the signed-zero control.

The [committed plan](https://github.com/ethan03805/enfusion-neural/blob/main/scenes/lighting-gpu-v1.json) fixes the numerical limits before implementation: residual absolute error at most 0.00001, and linear RGB error at most 0.00002 plus 0.00002 times the reference magnitude. Bounds, finite output, alpha and invalid-pixel fallback are separate checks. These are implementation tolerances, not relaxed image-fidelity gates.

All three variants pass at 1 × 1, 1 × 17, 31 × 1, 127 × 65, 480 × 270, 2560 × 1440 and 3840 × 2160. These controls use reproducible numerical fixtures. Their largest residual error is **0.0000010282**. The 112 rendered frames have maximum residual error **0.0000001881** and maximum linear RGB difference from the retained CPU images **0.000022889**, within the magnitude-dependent tolerance.

| Existing path | Frames | GPU/CPU agreement | Fidelity result |
| --- | ---: | --- | --- |
| Cross-courtyard test | 48 | Pass | All declared gates pass |
| Original room regression | 32 | Pass | Contrast gate untested: no marking panel |
| Partitioned room regression | 32 | Pass | All declared gates pass |

The test's mean log error improves **63.1% over source** and **26.6% over the stronger affine control**. Its temporal error increases **0.735%**, within the original 2% tolerance; temporal improvement is not established. The older specialized model remains more accurate in the original room. All these limitations survive the GPU port.

Only the locked full-input candidate's frame outputs and linear-space metrics were recomputed on the GPU. Other models remain the original CPU controls. No renders, training, checkpoint selection or threshold changes occurred. The [complete test and regression clips](lighting-diversity.md) remain the published CPU comparisons; they are not relabeled as newly captured GPU videos. Display-referred metrics were not recomputed in this numerical milestone.

## Timing

The 1440p full-input benchmark uses ten warmups and 100 measured dispatches on one prepared numerical fixture. Each dispatch includes its UAV barrier. Source upload and output readback occur once for the batch.

| Measurement | Observed |
| --- | ---: |
| Dispatch p50 | 0.962 ms |
| Dispatch p95 | 1.961 ms |
| One upload and transition | 13.410 ms |
| One readback and transition | 3.763 ms |
| Setup, including shader compilation | 3,775.76 ms |
| Native process, all 110 dispatches | 4,070.42 ms |
| Default source and output buffers | 450 MiB |

The buffer total excludes staging memory, driver allocations and peak application use. Inputs contain the ordered model features plus original RGB, alpha and a validity flag. Feature construction runs on the CPU before invocation. These measurements do not establish sustained frame rate, capture-to-present latency or net rendering savings. The upload/readback costs also show why a supported engine resource interface matters.

## Retained failures

The initial batch stopped after 19 successful controls when the drive filled while writing the next input; that GPU invocation never started. Lossless filesystem compression and verified regeneration of disposable numerical inputs recovered space. Original scene EXRs, GPU output records, shaders and failed artifacts remain. Every removed generated input has a recipe, source snapshots and a byte-exact regeneration check. Redundant derived NPY copies are recoverable from the retained native output.

The first RGB-only 4K shader then produced one residual of **0.2500000298023224**, outside the model's ±0.25 bound. Its numerical-error checks passed, while the separate bound check failed. The [declared follow-up](https://github.com/ethan03805/enfusion-neural/blob/main/scenes/lighting-gpu-bound-followup-v2.json) clamps the shader result to that original bound and repeats all 21 controls. The failed output remains in the evidence. A CPU test rejects the same one-step floating-point escape.

The original RGBA8 backend also passes its six hardware smoke sizes through 4K, with maximum RGB error 1 and exact random alpha. Twelve malformed native record/size cases are rejected before GPU setup. The CPU suite has 70 tests; CI includes the lighting smoke and explicitly skips hardware claims when no suitable GPU exists.

## Reproduce and continue

```powershell
cmake --build build --config Release
python scripts/check_native_contract.py
python scripts/gpu_lighting_smoke.py --compact-inputs --out experiments/local/lighting-gpu-new
```

The rendered-frame check uses `scripts/evaluate_lighting_gpu.py` with the existing test/regression source roots and retained CPU evaluation roots. Use the documented NumPy/OpenEXR environment and a new output directory. It retains every native output and reconstructs temporary transfer buffers from the original source records. `scripts/summarize_lighting_gpu.py` binds native outputs, recipes, frozen models, frame metrics and both initial failures. Run `--help` for required paths.

Next, establish the supported Enfusion feature and execution contract. Validate color, surface information, frame identity and output placement against controlled scenes, then test the model on actual Arma towns, interiors, foliage, vehicles and characters. The separately working [color lookup](color-lookup.md) cannot execute this scene-conditioned graph. Complete-frame timings must follow that integration.

[All measurements, frame metrics and failures](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/lighting-gpu-v1.json) · [Model lock](https://github.com/ethan03805/enfusion-neural/blob/main/models/lighting-diversity-v1/model-lock.json) · [Architecture](architecture.md)
