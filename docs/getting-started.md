# Get started

For the tested current-PC package, use the [Windows download and controls](playable.md#run-the-build). The live companion needs Windows and the installed Steam game. Python 3 starts the isolated session; neural inference itself is native.

## Build the live companion

Visual Studio C++ tools, a Windows SDK and CMake are required. C++20 avoids the deprecated coroutine headers selected by older C++ modes in newer MSVC versions.

```powershell
git clone https://github.com/ethan03805/enfusion-neural.git
cd enfusion-neural
py -3 -m venv .venv
.venv/Scripts/python -m pip install -e .
.venv/Scripts/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
cmake -S native -B build -A x64
cmake --build build --config Release
.venv/Scripts/python scripts/prepare_pretrained.py --model zero-dce-plusplus
Start-Playable.cmd
```

PyTorch is only needed to verify/export the author's checkpoint. Downloads are pinned and hash-checked. The exported weights retain separate academic/noncommercial terms. Runtime inference needs neither PyTorch nor CUDA.

The launcher discovers the default Steam game path and a saved Documents/OneDrive Documents profile. For other locations, `scripts/launch_playable.py` accepts `--game`, `--settings-source` and `--out`. It returns the game PID for `enr_companion.exe --pid PID --out NEW_DIRECTORY --overlay --mode neural --model weights.bin`.

## Verify and measure

```powershell
.venv/Scripts/python -m unittest discover -s tests -v
.venv/Scripts/python scripts/build_docs.py
.venv/Scripts/python scripts/benchmark_playable.py --out runs/town-standard --preset standard --trace cpu
.venv/Scripts/python scripts/analyze_playable.py runs/town-standard
```

The measurement runner expects the official [PresentMon 2.5.1 Windows executable](https://github.com/GameTechDev/PresentMon/releases/tag/v2.5.1) at `runs/tools/PresentMon-2.5.1-x64.exe`. `--record` additionally requires an FFmpeg build with WGC gfxcapture and AMD AMF encoding. It adds explicit readback/conversion costs and must be measured separately.

Run one benchmark at a time. The addon uses engine actions for a repeatable local walking/turning sequence. Each run verifies requested rendering settings and keeps game, companion and measurement logs. Retain failures, use a fresh output directory and never stop unrelated game, editor or trace processes.

Package a verified build with `scripts/package_playable.py --out runs/deliverables/NEW_BUILD_NAME`. Keep packages outside `dist/`, which is reserved for the documentation site.

## Background tools

The original procedural training and offline D3D12 reference remain available through `python -m enr.cli`. They do not measure live application performance. See the [research archive](research-history.md) and [architecture](architecture.md).

Enfusion Lab remains the isolated Workbench dependency for addon validation and controlled exports. Its `doctor`, `init`, `validate` and `capture` commands retain their own project and logs. No Steam files belong in an experiment.
