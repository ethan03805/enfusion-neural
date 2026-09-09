# Enfusion Neural

Offline neural image processing and capture tools for Enfusion Workbench.

[Documentation](https://ethan03805.github.io/enfusion-neural/) · [Current status](docs/status.md) · [Roadmap](docs/roadmap.md)

The first milestone is a **working offline neural pipeline**: train a 251-parameter residual CNN, run its generated shader on a real D3D12 GPU, and compare the result with an independent NumPy reference. It accepts arbitrary supported image dimensions and preserves alpha exactly.

The [reference scene pack](docs/reference-scenes.md) adds three static camera/lighting variants, a batch capture command and repeatability analysis. Its first nine captures share verified camera/environment controls but retain measurable pixel variation.

The [camera-path adapter](docs/capture-controls.md) records verified sample telemetry and an [80-frame before/after video](docs/comparisons.md#motion). An original [material room](docs/material-room.md) adds aligned synthetic lighting targets, EXR passes and a reference-noise check. Workbench viewport scale/FSR and an aligned Enfusion appearance pair remain open.

The [lighting study](docs/lighting-study.md) trains a separate scene-conditioned model on 18 controlled synthetic cases and publishes before/after/reference images. It improves held-out view/light combinations within one room; engine integration, other assets, temporal fidelity and net frame savings remain unverified. Read the [technical feasibility review](docs/feasibility.md) before scaling asset-specific training.

The [frozen-model motion test](docs/lighting-motion.md) adds 64 frames across the original room and a new partitioned layout, with independently sampled references and synchronized comparison clips. The model improves average error but loses its advantage over simpler methods on the new layout and makes marking contrast less accurate. Those regressions guide the next data/model experiment.

This is the foundation, not a photorealistic model or a live game renderer. Access to Enfusion's scene buffers and a supported presentation path remains unresolved. The initial product target is **1440p at 20 FPS or better on the recorded test configuration**, prioritizing fidelity and scene identity. A single-image reconstruction baseline cannot establish that target.

## Run

Requirements: Python 3.9–3.12, NumPy/Pillow; Windows, CMake and Visual Studio C++ tools for the GPU backend. No CUDA, downloaded model or cloud account is required.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e .
cmake -S native -B build -A x64
cmake --build build --config Release
.venv\Scripts\python -m enr.cli benchmark --model models/bootstrap-v0.json --out runs/first
```

The benchmark defaults to 2560x1440. Use `--image path/to/frame.png` for an exported scene, or `--width 1920 --height 1080` for a different measurement size. Choose a new output directory for each run. It retains output images, shader, raw GPU samples, hashes and CPU comparison in `run.json`.

```powershell
python -m enr.cli train --out runs/new-model.json --steps 1200
python -m enr.cli evaluate --model runs/new-model.json --out runs/new-evaluation
python -m unittest discover -s tests -v
```

Activate your environment or substitute its Python path for these commands. Training fits all weights on the local CPU in a tiny workload; neural inference runs on the GPU. The current shader specializes weights at process startup, included in setup timing.

## Contribute

Start with [AGENTS.md](AGENTS.md), [architecture](docs/architecture.md) and the [handoff](docs/status.md). The repository keeps documentation in Markdown and publishes it through GitHub Actions to GitHub Pages. See [contributing](docs/contributing.md) for local site preview and validation.

Code and original procedural fixtures are MIT licensed. Selected [comparison screenshots](docs/comparisons.md) are published with attribution; their game content is outside the code license. Raw capture collections and game assets remain excluded. This is an independent research project, unaffiliated with Bohemia Interactive or AMD.
