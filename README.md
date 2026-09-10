# Enfusion Neural

A Windows companion and isolated local single-player addon for Arma Reforger. The companion captures game RGB, estimates neural exposure curves on the GPU and displays the result with a source bypass. Target: **2560 × 1440 at 30–60 FPS on RX 7800 XT**.

[Documentation](https://ethan03805.github.io/enfusion-neural/) · [Current status](docs/status.md) · [Playable work log](docs/playable.md) · [Roadmap](docs/roadmap.md)

This is a research prototype. Substantial photorealistic material and lighting improvement has not been achieved. The [Windows build, unretimed gameplay and measured comparison](https://ethan03805.github.io/enfusion-neural/playable.html) are available; physical input and broader fidelity acceptance remain open. Earlier Blender lighting and offline studies stay in the research archive.

## Play

Use the prepared Windows package, or build and prepare weights below. Close other Reforger sessions, then double-click **Start-Playable.cmd**. It creates a fresh private profile and addon copy, launches the town scene and starts the companion. It requires a local Steam installation and Python 3; inference has no Python or PyTorch dependency.

- **F8:** expose the original game / resume enhancement.
- **F9:** switch the companion between identity and enhancement.
- **F10:** exit the companion; the original game continues.

Optional: `Start-Playable.cmd --scene town-evening --preset combined --strength 0.35`. Scene choices: town, town-evening, foliage. The free-play launcher does not run the automatic benchmark path. Sessions, source settings copies and timestamp logs stay under ignored `runs/`.

## Build and validate

```powershell
py -3 -m venv .venv
.venv/Scripts/python -m pip install -e .
.venv/Scripts/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
cmake -S native -B build -A x64
cmake --build build --config Release
.venv/Scripts/python scripts/prepare_pretrained.py --model zero-dce-plusplus
.venv/Scripts/python -m unittest discover -s tests -v
.venv/Scripts/python scripts/build_docs.py
```

Visual Studio 2022 C++ tools and Windows SDK are required to build. PyTorch is needed only to verify/export pretrained tensors and run independent numerical evaluation. The live companion uses native D3D11 and Windows Graphics Capture.

For measurements, see `scripts/benchmark_playable.py` and `scripts/analyze_playable.py`. The benchmark launches a fresh game, verifies active settings, follows the declared path and retains PresentMon and companion traces. It requires the separately downloaded PresentMon tool described in the work log. Recording runs are labeled separately because encoding adds overhead.

## Contribute and licenses

Start with [AGENTS.md](AGENTS.md), [architecture](docs/architecture.md) and [contributing](docs/contributing.md). GitHub Actions publishes the Markdown documentation to the existing GitHub Pages site.

Repository code and original procedural fixtures are MIT licensed. Zero-DCE++ checkpoints and author code have separate academic/noncommercial terms; Image-Adaptive-3DLUT has separate Apache-2.0 terms. Game imagery belongs to Bohemia Interactive and is outside the code license. No game assets are included in the addon or package. This is an independent project, unaffiliated with Bohemia Interactive or AMD.
