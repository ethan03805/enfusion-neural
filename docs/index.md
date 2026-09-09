# Enfusion Neural

This repository contains Workbench capture tools, reference scene definitions, a small neural image-processing model and a native D3D12 backend. The current workflow operates on exported images.

## Start here

| Read | Purpose |
| --- | --- |
| [Objectives](vision.md) | Image fidelity requirements and evaluation targets |
| [Get started](getting-started.md) | Build, train and run the first neural component |
| [Reference scenes](reference-scenes.md) | Capture repeated views and measure image differences |
| [Capture controls](capture-controls.md) | Camera path, verified settings and remaining viewport limitations |
| [Material room](material-room.md) | Original geometry and aligned synthetic lighting targets |
| [Lighting study](lighting-study.md) | Trained lighting correction, baselines and held-out comparisons |
| [Technical feasibility](feasibility.md) | Workbench interfaces, asset-specific training and photographic references |
| [Comparisons](comparisons.md) | Inspect source/output images and synchronized motion |
| [Architecture](architecture.md) | Model, GPU backend and engine boundaries |
| [Evidence](evidence.md) | Measured results and what they establish |
| [Roadmap](roadmap.md) | Next experiments and acceptance gates |
| [Handoff](status.md) | Current state for the next engineer or agent |

## What exists

A small trainable convolutional network, an independent CPU reference, a native D3D12 inference executable and a reproducible Workbench capture workflow. Source, model weights and measurement summaries live together in the repository.

The bootstrap model reconstructs procedurally degraded images. A separate [lighting model](lighting-study.md) learns a restricted diffuse-light contribution from original scene buffers and improves held-out camera/light combinations within one room. Neither delivers the project's photorealism goal. Live Enfusion integration, new-asset generalization and temporal stability remain open.

The initial playable floor is **2560 × 1440 at 20 FPS on a declared test configuration**. This is a target for the complete application. GPU dispatch timings alone cannot demonstrate it.
