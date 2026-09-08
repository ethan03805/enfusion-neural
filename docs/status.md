# Handoff

Updated 8 September 2026. Milestone: offline neural foundation, v0.1. Read [vision](vision.md) before choosing the next model or performance target.

## Implemented and checked

- Original procedural training data and a 251-parameter residual CNN with all weights trained locally.
- Versioned JSON model, bounded residual, independent CPU inference and numerical gradient checks.
- Native D3D12 FP32 inference on RX 7800 XT, including raw timestamps and separate file-pipeline measurements.
- CPU/GPU pixel agreement at 1440p and on an actual Enfusion capture; random-alpha and dimension checks through 4K.
- Enfusion Lab doctor, isolated addon compile validation and visually inspected Arland capture.
- Twelve-page Markdown documentation site, shared agent/human protocol, Linux CPU CI, Windows build/smoke workflow and GitHub Pages deployment workflow.

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

## Next task

Implement the reference scene/configuration manifest and repeatability experiment described in [roadmap gate 02](roadmap.md#02-reference-scenes-and-appearance-data). Resolve how aligned appearance targets will be obtained before training a photorealistic enhancement model. Investigate the supported renderer bridge as a separate bounded research task.

The owner's confirmed priorities are visual fidelity, photorealism without scene/identity distortion, and a 1440p/20 FPS playable floor on RX 7800 XT. Do not revert to the earlier 60 FPS reconstruction-first proposal. The bootstrap CNN is a control for learning and GPU execution, not the final model architecture.
