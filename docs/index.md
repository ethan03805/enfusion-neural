# Enfusion Neural

Photorealism that stays faithful to the scene.

The aim is richer lighting and more convincing materials without changing the people, objects or visibility that make the simulation meaningful. Arma Reforger is the first proving ground. The rendering core will remain independent of Enfusion so each future integration has an explicit contract.

## Start here

| Read | Purpose |
| --- | --- |
| [Vision](vision.md) | Fidelity goals and the 7800 XT target |
| [Get started](getting-started.md) | Build, train and run the first neural component |
| [Architecture](architecture.md) | Model, GPU backend and engine boundaries |
| [Evidence](evidence.md) | Measured results and what they establish |
| [Roadmap](roadmap.md) | Next experiments and acceptance gates |
| [Handoff](status.md) | Current state for the next engineer or agent |

## What exists

A small trainable convolutional network, an independent CPU reference, a native D3D12 inference executable and a reproducible Workbench capture workflow. Source, model weights and measurement summaries live together in the repository.

The current model reconstructs procedurally degraded images. It verifies the learning and execution path; it does not deliver the project's photorealism goal. Live Enfusion integration, material-aware enhancement and temporal stability are still open work.

The initial playable floor is **2560 × 1440 at 20 FPS on an RX 7800 XT**. This is a target for the complete application. GPU dispatch timings alone cannot demonstrate it.
