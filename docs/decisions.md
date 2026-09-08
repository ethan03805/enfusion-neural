# Decisions

## 001 · Fidelity before throughput

Accepted 8 September 2026. The target is photorealism that preserves scene identity, with 1440p/20 FPS as the local playable floor. This supersedes the earlier provisional 60 FPS reconstruction-first direction. Fifty milliseconds is the full-frame budget. Other resolutions remain required.

## 002 · Keep the first neural graph small

Accepted for the bootstrap milestone. A 251-parameter CNN makes gradient checks, CPU/GPU parity and complete inspection practical. It trains all layers from original procedural fixtures and runs through native D3D12. Its reconstruction task is a reference problem, not the final fidelity model.

## 003 · Separate offline evidence from integration

Accepted. Enfusion Lab provides editor capture and compile validation. No demonstrated native resource bridge exists in this project. Workbench screenshots do not prove motion-vector access, linear scene color, runtime presentation or Workshop distribution.

## 004 · Native fixed-graph backend first

Accepted for v0. Reuse the installed Windows graphics toolchain rather than introducing a large ML stack for 251 parameters. Specialize weights at startup and report compilation cost separately. This trades generality for auditability. Evaluate WinML/ONNX Runtime when the appearance graph grows; record operator partitioning and avoid hidden CPU fallback.

Current ONNX Runtime documentation places DirectML in sustained engineering and points new Windows feature development toward WinML. That informs a future runtime evaluation, not a requirement to rewrite the small HLSL reference. See [sources](sources.md).

## 005 · Portable documentation in the code repository

Accepted. Markdown is canonical. A small static build creates GitHub Pages with shared navigation, responsive typography and no client framework. AGENTS.md is the shared engineering protocol; CLAUDE.md links to it. Keep game captures and machine profiles local, with reviewed numerical evidence in Git.

## 006 · Begin with measured scene repeatability

Accepted 8 September 2026. The first scene pack uses three explicit camera/lighting variants in the installed Arland world. It controls and verifies date, time, weather and wind through a project-owned extension of Enfusion Lab's adapter. It keeps the plugin's process ownership and capture checks. The installed plugin is unchanged.

The views overlap and remain one diagnostic group. A repeated scene is not automatically a training target or a new independent test scene. Render scale, FSR, quality preset and projection remain null until verified. Nonzero image differences are retained rather than corrected away.

## 007 · Documentation presentation

Accepted 8 September 2026. Remove the logo and promotional copy from the site, keep personal computer specifications out of rendered documentation, and provide a system/light/dark theme preference. Preserve hardware details in raw benchmark records so measurement provenance is not lost.

## 008 · Publish traceable visual comparisons

Accepted 8 September 2026 at the user's request. Publish the existing Arland benchmark pair and the first capture from each reference scene variant. Keep image bytes unchanged, record provenance in the media manifest and check their hashes during the site build. These screenshots are outside the MIT code license; include game attribution and the content usage policy.

Show the model's visible failures alongside its numerical results. Use a manual comparison slider with a static fallback. Independent still captures are not a motion sequence; publish before-and-after video only when source and output frames can be synchronized and playback conditions documented.
