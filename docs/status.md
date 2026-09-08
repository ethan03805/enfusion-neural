# Handoff

Updated 8 September 2026. Milestone: published visual comparisons and reference scene gallery. Read [objectives](vision.md) before choosing the next model or performance target.

## Implemented and checked

- Original procedural training data and a 251-parameter residual CNN with all weights trained locally.
- Versioned JSON model, bounded residual, independent CPU inference and numerical gradient checks.
- Native D3D12 FP32 inference on the recorded test configuration, including raw timestamps and separate file-pipeline measurements.
- CPU/GPU pixel agreement at 1440p and on an actual Enfusion capture; random-alpha and dimension checks through 4K.
- Enfusion Lab doctor, isolated addon compile validation and visually inspected Arland capture.
- Three diagnostic scene variants with explicit camera, date, time, weather and wind controls; nine independent captures and all nine pairwise comparisons.
- Telemetry and image-hash checks, dataset-group split validation, unaligned image errors and a bounded integer alignment estimate.
- Fourteen-page Markdown documentation site with system/light/dark themes and an accessible before-and-after comparison; shared agent/human protocol, Linux CPU CI, Windows build/smoke workflow and GitHub Pages deployment workflow.
- Five reviewed screenshots published without image transformations, with source records, hashes and attribution. Model output was checked against retained GPU output bytes and the CPU reference before publication. No continuous motion sequence has been recorded.

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

Pin render scale, FSR, quality preset and camera projection for the scene pack. Investigate residual image differences before calling the capture deterministic. Then add an original controlled scene with known geometry/materials and define aligned appearance targets. See [reference scenes](reference-scenes.md) and [roadmap gate 02](roadmap.md#02-reference-scenes-and-appearance-data). The supported renderer bridge remains a separate research task.

The first measured reference batch is retained locally under `experiments/local/reference-v1/`; its reviewed numerical report is `evidence/reference-scenes-v1.json`. All camera/environment checks passed, but every scene had nonzero pixel variation. These captures remain diagnostic data, not supervised appearance targets.

The project priorities are visual fidelity, photorealism without scene/identity distortion, and a 1440p/20 FPS playable floor on the recorded test configuration. Do not revert to the earlier 60 FPS reconstruction-first proposal. The bootstrap CNN is a control for learning and GPU execution, not the final model architecture.
