# Bootstrap v0

Purpose: verify training, fixed-graph GPU execution and CPU/GPU agreement. **Not a photorealistic model, game enhancement release or temporal renderer.**

| Field | Value |
| --- | --- |
| File | `bootstrap-v0.json` |
| Architecture | 3×3 RGB → 8 ReLU channels → 1×1 RGB residual |
| Parameters | 251, all trained |
| Input | HWC display-referred RGB normalized to [0,1] |
| Borders | Edge replication |
| Residual | Clamped to ±0.125; final RGB clamped to [0,1] |
| Alpha | Passed through bit-exactly in the file/GPU pipeline |
| Training | NumPy CPU; Adam; 1,200 steps; batch 1,024; seed 7 |
| Data | Original procedural gradients, lines and rectangles; no external assets |
| Degradation | Bicubic half-size → bicubic original-size |
| Splits | Train scene seeds 0–11, validation 100–103, test 200–203 |
| Backend | FP32 HLSL / native D3D12; independent NumPy reference |
| License | MIT for code, original fixtures and these trained weights |

The model slightly improves reconstruction PSNR on the four fixed test fixtures. It has no training data for faces, foliage, material physics, realistic illumination or temporal consistency. Visual inspection of the first Arland output found exaggerated edges and dark foliage boundaries. Do not display its output as a faithful photorealistic transformation.

No reconstruction method can guarantee recovery of absent scene information. A bounded residual limits color change but does not guarantee silhouette, identity or visibility preservation. No HDR, depth, motion or protected-HUD contract exists in v0.

Reproduce training with `python -m enr.cli train --out runs/retrained.json --steps 1200 --seed 7`. Metadata includes wall time, so the complete JSON hash can differ even for identical weights. Floating-point training may vary between NumPy/BLAS platforms. Compare weights and metrics; benchmark manifests identify the exact evaluated model hash.
