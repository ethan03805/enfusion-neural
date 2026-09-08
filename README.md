# Enfusion Neural

Faithful photorealism for Enfusion, beginning with Arma Reforger and the AMD RX 7800 XT.

[Documentation](https://ethan03805.github.io/enfusion-neural/) · [Current status](docs/status.md) · [Roadmap](docs/roadmap.md)

The first milestone is a **working offline neural pipeline**: train a 251-parameter residual CNN, run its generated shader on a real D3D12 GPU, and compare the result with an independent NumPy reference. It accepts arbitrary supported image dimensions and preserves alpha exactly.

This is the foundation, not a photorealistic model or a live game renderer. Access to Enfusion's scene buffers and a supported presentation path remains unresolved. The initial product target is **1440p at 20 FPS or better on RX 7800 XT**, prioritizing fidelity and scene identity. A single-image reconstruction baseline cannot establish that target.

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

Code and original procedural fixtures are MIT licensed. Bohemia game assets and local captures are excluded. This is an independent research project, unaffiliated with Bohemia Interactive or AMD.
