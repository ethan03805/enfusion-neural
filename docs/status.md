# Handoff

Updated 8 September 2026. Milestone: a controlled synthetic lighting reconstruction study and an installed-SDK feasibility review. Read [objectives](vision.md) before choosing the next model or performance target.

## Implemented and checked

- Original procedural training data and a 251-parameter residual CNN with all weights trained locally.
- Versioned JSON model, bounded residual, independent CPU inference and numerical gradient checks.
- Native D3D12 FP32 inference on the recorded test configuration, including raw timestamps and separate file-pipeline measurements.
- CPU/GPU pixel agreement at 1440p and on an actual Enfusion capture; random-alpha and dimension checks through 4K.
- Enfusion Lab doctor, isolated addon compile validation and visually inspected Arland capture.
- Three diagnostic scene variants with explicit camera, date, time, weather and wind controls; nine independent captures and all nine pairwise comparisons.
- Telemetry and image-hash checks, dataset-group split validation, unaligned image errors and a bounded integer alignment estimate.
- Eighteen-page Markdown documentation site with system/light/dark themes, still comparisons and a synchronized video; shared agent/human protocol, Linux CPU CI, Windows build/smoke workflow and GitHub Pages deployment workflow.
- Eighty camera-path samples at 2560 × 1440, each with a GPU output checked against the independent CPU reference. One encoded stream keeps before/after playback synchronized. It is a retimed offline sequence, not live performance.
- Camera projection, exposure, environment and selected engine settings readback checks. Three final static repeats and an earlier probe batch remain documented, including nonzero pixel differences.
- Original material room generated with Blender Cycles, limited-bounce source, multi-bounce reference and independent-seed noise check. Exact source/reference depth and object-ID agreement; scene-linear RGBA and auxiliary EXR passes retained locally. This is synthetic data, not an Enfusion/reference pair.
- Sixteen reviewed PNGs and one video with source records, hashes and attribution. The video and its poster explicitly record their scaling and compression; original source/model frame PNGs remain available.
- Eighteen original lighting cases with paired diffuse-bounce controls, 12 training/two validation/three test/one stress splits within one scene group, and two independent-seed reference checks. A 1,827-parameter scene-conditioned CPU model beats RGB-only and affine controls on the three test cases. Weights, gradients, serialization, features and partitioned inference are checked. See [lighting study](lighting-study.md); no game-frame saving or temporal fidelity is established.
- Read-only [technical feasibility review](feasibility.md) of installed SDK declarations, asset-specific representations, photographs and data-use scope. Material replacement is documented; native scene buffers and output composition remain unverified.

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

Add a distinct original scene family and a smooth held-out camera/light path to the lighting study. Preserve markings and occlusion boundaries. Acceptance: fixed splits before training, an independent reference-noise check, improvement over identity/RGB/affine baselines, and reported boundary/temporal failures. The current model only learned one room; none of its test combinations establishes new-asset generalization.

In parallel, identify an authoritative supported renderer extension for a minimal identity/inversion control. Verify source color, required surface inputs, synchronization and presentation before scaling Reforger asset training. The [feasibility report](feasibility.md) separates documented declarations from tested capabilities. No native lighting-model implementation or timing exists yet.

Current lighting evidence: `experiments/local/lighting-study-v1/` (18 rendered cases), `experiments/local/lighting-fit-v1b/` (published weights and predictions), and `evidence/lighting-study-v1.json` (all metrics and source records). Earlier `lighting-fit-v1/` is retained; it has identical numerical outputs before adding the portable JSON model contract. Both fits use the same fixed plan and hyperparameters.

## Prior capture work

Resolve internal Workbench viewport render scale and FSR. The diagnostic save succeeded, and a black-frame control confirms that the isolated file loads. Neither the diagnostic scale presets nor the settled workspace controls established the required viewport effect. The separate render-target callback rejected export. See [capture controls](capture-controls.md#diagnostic-investigation) and `evidence/viewport-probes-v1.json` before repeating these attempts.

Next acceptance criteria: identify a supported setting or diagnostic that belongs to the main viewport, obtain its effective internal dimensions and FSR state, then demonstrate a corresponding image change with a reduced-resolution control. Only after that should a full-resolution, FSR-disabled preset receive three independent repeat captures. `scripts/probe_viewport.py` reproduces the current unresolved probes; its successful exit means the investigation ran, not that viewport controls were verified.

The subsequent native UI inspection and one post-startup `UserSettingsChanged()` probe did not resolve this. Their observations and run hashes are retained in `evidence/viewport-followup-v1.json`. The isolated inspection window was closed normally; no other editor was changed. No accepted scale/FSR preset is available yet.

Next, import the original material-room geometry into an isolated Enfusion scene and validate matching camera, materials, light and color conventions before using engine/reference pairs for training. The accepted synthetic pair only validates the reference-generation method. See [material room](material-room.md) and [roadmap gate 02](roadmap.md#02-reference-scenes-and-appearance-data). The supported renderer bridge remains a separate research task.

Current local evidence: `experiments/local/motion-static-v1c/` for final repeats; `experiments/local/motion-v1b/runs/20260909T003650-5d8d09c360/` for the 80-frame sequence; `experiments/local/motion-output-v1/` for GPU outputs and video; `experiments/local/material-room-v1d/` for the accepted synthetic pair. Earlier probes and failed runs were retained. Portable reports are `evidence/capture-controls-v1.json`, `evidence/motion-v1.json` and `evidence/material-room-v1.json`.

The first measured reference batch is retained locally under `experiments/local/reference-v1/`; its reviewed numerical report is `evidence/reference-scenes-v1.json`. All camera/environment checks passed, but every scene had nonzero pixel variation. These captures remain diagnostic data, not supervised appearance targets.

The project priorities are visual fidelity, photorealism without scene/identity distortion, and a 1440p/20 FPS playable floor on the recorded test configuration. Do not revert to the earlier 60 FPS reconstruction-first proposal. The bootstrap CNN is a control for learning and GPU execution, not the final model architecture.
