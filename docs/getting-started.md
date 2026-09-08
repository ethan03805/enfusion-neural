# Get started

Clone the repository, then create an isolated Python 3.9–3.12 environment. The CPU path also runs on Linux; the native GPU backend currently requires Windows with CMake, a Windows SDK and Visual Studio C++ tools.

```powershell
git clone https://github.com/ethan03805/enfusion-neural.git
cd enfusion-neural
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e .
cmake -S native -B build -A x64
cmake --build build --config Release
.venv\Scripts\python -m enr.cli benchmark --model models/bootstrap-v0.json --out runs/first
```

The final command creates an original procedural fixture, runs the learned network at 1440p on the selected hardware GPU and checks every RGB pixel against the NumPy reference. Alpha must match exactly. Floating-point implementation differences permit at most one 8-bit RGB code value. A mismatch exits with failure and retains the artifacts.

`run.json` contains input and model hashes, dimensions, adapter, comparison results and raw dispatch timing samples. The file pipeline includes setup, compilation and 110 dispatches. It is not the latency of one live frame.

## Train and evaluate

```powershell
.venv\Scripts\python -m enr.cli train --out runs/candidate.json --steps 1200
.venv\Scripts\python -m enr.cli evaluate --model runs/candidate.json --out runs/candidate-eval
```

Training uses original procedural images, a reproducible random seed and all 251 trainable parameters. Separate scene seeds define train, validation and held-out test sets. Evaluation compares against bicubic downsampling followed by bicubic upsampling. It is not an FSR comparison or a photorealism score.

## Use an Enfusion frame

Install or use the existing Enfusion Lab plugin. Its `doctor` discovers stable game and Workbench installations. Initialize a dedicated empty experiment directory, validate the addon, and capture with an explicit world and camera. The plugin must remain a separate dependency; no Steam files belong in this repository.

```powershell
enfusion-lab doctor --json
enfusion-lab init experiments/local --json
enfusion-lab validate --project experiments/local --json
enfusion-lab capture --project experiments/local --position 2048 60 2048 --direction 1 0 0 --settle 5 --timeout 120 --json
```

The installed CLI may instead be invoked as `python -m enfusion_lab` from its package checkout. If using MCP, the equivalent tools are `doctor`, `init`, `validate` and `capture`; pass absolute paths. Review the returned status, actual full-size PNG and camera metadata.

```powershell
.venv\Scripts\python -m enr.cli benchmark --model models/bootstrap-v0.json --image path/to/frame.png --out runs/arland-first
```

Capture opens its own Workbench simulation window and ends its owned process after export. Successful export may have a child exit code of 1; the outer run status is authoritative. Validation must compile and exit naturally with 0.

## Failure recovery

Use a fresh output directory when a command reports that one exists. Retain failed runs. For CMake errors, confirm the desktop C++ workload and SDK. A missing hardware D3D12 adapter is a failure, not a CPU fallback. Shader compilation logs are printed on error. If Workbench fails, inspect that run's logs and never kill other editor processes by name.
