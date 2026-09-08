# Decisions

## 001 · Fidelity before throughput

Accepted 8 September 2026 after owner clarification. The target is photorealism that preserves scene identity, with 1440p/20 FPS as the local playable floor. This supersedes the earlier provisional 60 FPS reconstruction-first direction. Fifty milliseconds is the full-frame budget. Other resolutions remain required.

## 002 · Keep the first neural graph small

Accepted for the bootstrap milestone. A 251-parameter CNN makes gradient checks, CPU/GPU parity and complete inspection practical. It trains all layers from original procedural fixtures and runs through native D3D12. Its reconstruction task is a reference problem, not the final fidelity model.

## 003 · Separate offline evidence from integration

Accepted. Enfusion Lab provides editor capture and compile validation. No demonstrated native resource bridge exists in this project. Workbench screenshots do not prove motion-vector access, linear scene color, runtime presentation or Workshop distribution.

## 004 · Native fixed-graph backend first

Accepted for v0. Reuse the installed Windows graphics toolchain rather than introducing a large ML stack for 251 parameters. Specialize weights at startup and report compilation cost separately. This trades generality for auditability. Evaluate WinML/ONNX Runtime when the appearance graph grows; record operator partitioning and avoid hidden CPU fallback.

Current ONNX Runtime documentation places DirectML in sustained engineering and points new Windows feature development toward WinML. That informs a future runtime evaluation, not a requirement to rewrite the small HLSL reference. See [sources](sources.md).

## 005 · Portable documentation in the code repository

Accepted. Markdown is canonical. A small static build creates GitHub Pages with shared navigation, responsive typography and no client framework. AGENTS.md is the shared engineering protocol; CLAUDE.md links to it. Keep game captures and machine profiles local, with reviewed numerical evidence in Git.
