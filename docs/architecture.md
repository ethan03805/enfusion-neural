# Architecture

The current execution path is deliberately small enough to inspect from end to end.

```text
Enfusion Lab export or original procedural fixture
             ↓ PNG / display-referred RGBA8
        Python input validation
             ↓ packed RGBA8 + generated model shader
       Native D3D12 executable
             ↓ upload → CNN dispatch → readback
        Output PNG + timing samples
             ↓
       Independent NumPy comparison
```

## Boundaries

| Component | Responsibility |
| --- | --- |
| `enr/data.py` | Original fixtures and explicit degradation |
| `enr/model.py` | Model contract, gradients, CPU inference, HLSL generation |
| `enr/cli.py` | Training, evaluation, benchmark orchestration and manifests |
| `enr/references.py` | Scene pack validation, batch capture and repeat comparisons |
| `enr/sequence.py` | Isolated camera-path sampling and capture contract verification |
| `enr/motion.py` | Per-frame GPU/CPU verification and synchronized video encoding |
| `scripts/render_material_room.py` | Original Cycles scene and aligned reference generation |
| `scripts/check_material_room.py` | All-part EXR validation, geometry and noise checks |
| `scenes/` | Versioned scene definitions and control settings |
| `adapters/enfusion/` | Project-owned extension of the Workbench capture script |
| `native/enr_gpu.cpp` | Hardware adapter, D3D12 buffers, dispatch, timestamps and readback |
| Enfusion Lab | External Workbench addon validation and image capture |
| `docs/` | Maintained engineering documentation |
| `evidence/` | Reviewed portable measurement summaries |

The native backend uses one immutable source buffer and one output buffer per process. Ten warmup dispatches and 100 measured dispatches reuse those buffers. A UAV barrier follows each dispatch. Input is uploaded once; output is read back once. This benchmark measures repeated computation on one frame. It does not include capture or presentation.

Weights are embedded into generated HLSL and compiled at startup. Compilation belongs to setup timing, never dispatch timing. This design is suitable for a fixed tiny reference graph; it is not a general model runtime. Evaluate WinML/ONNX Runtime and a reusable native context when larger models justify them.

## The v0 graph

An edge-padded 3 × 3 RGB neighborhood becomes 27 values. A learned 27-to-8 convolution, ReLU and 8-to-3 convolution predict an RGB residual. Clamp the residual to ±0.125, add it to the centre pixel, clamp to [0,1], and round to RGBA8. Preserve source alpha exactly. Total trainable parameters: 251.

All weights are trained with Adam and mean squared error on the local CPU. FP32 HLSL performs inference on the GPU. Neither CUDA nor a model download is needed. A bounded residual limits magnitude; it does not prove semantic or temporal safety.

The CPU reference processes row tiles with one-pixel halos to bound intermediate memory. It must match untiled convolution at tile boundaries, corners and odd sizes. RGB values are display-referred code values; they are not linear radiance or HDR.

The file backend accepts dimensions from 1 to 16,384 per axis, with at most 16,776,960 pixels in one dispatch. These are implementation limits, not recommended playback sizes. Floating-point and 16-bit image modes are rejected; color conversion or HDR support must be explicit.

## Future frame contract

Before live integration, a versioned frame must identify color format and transfer, dimensions, frame ID, timestamp, camera/projection and exposure convention. Optional depth, normals, motion, material data and protected masks need explicit availability flags and separate validation.

Native integration must establish device/queue ownership, resource lifetime, barriers, fences and the presentation stage. Reset temporal history on camera cuts, resolution changes, scope transitions, invalid inputs and device recreation. Until a supported bridge proves these rules, image export remains the only implemented Enfusion interface.

## Lighting study

The [lighting experiment](lighting-study.md) is a separate CPU reference in `enr/lighting.py`. Original Cycles source passes and scene constants provide 20 features: log-radiance, position, normal, material values, view direction and light offset. A 20 → 32 → 32 → 3 network predicts a bounded log-radiance residual. A separate RGB-only network and affine fit provide controls. This graph does not use the native v0 shader or inherit its timings.

`scripts/render_lighting_study.py` changes only diffuse-bounce depth within each pair. `scripts/train_lighting_study.py` validates hashes and alignment, fits only training cases, and selects checkpoints on validation cases. `scripts/display_lighting_study.py` applies the recorded display transform; `scripts/summarize_lighting_study.py` checks the conversion and retains metrics for every case, including independent-seed reference checks. Models carry a versioned feature/color contract and normalization statistics.

This experiment keeps the scene's original material information. It tests the value of supplying source surface data to lighting reconstruction; it does not infer missing textures or establish that Enfusion exposes these inputs. See [technical feasibility](feasibility.md) before changing the integration architecture or scaling asset collection.

The [motion evaluator](lighting-motion.md) loads the frozen JSON models and original affine coefficients without fitting. `scripts/render_lighting_motion.py` builds two versioned scenes directly and produces source, paired and independent references. `enr/temporal.py` validates camera paths and reprojects static source positions into the previous camera. Object-ID, normal and position checks select correspondences; excluded regions retain separate spatial metrics. This diagnostic uses Cycles passes and does not implement engine motion-vector access.

`scripts/summarize_lighting_motion.py` validates display conversions and records all frames, regions and transitions. `scripts/video_lighting_motion.py` verifies input hashes and encodes source/model/independent-reference images into a single synchronized stream. Portable evidence uses stable LF bytes where another artifact hashes it.
