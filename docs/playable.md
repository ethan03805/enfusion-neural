# Playable companion

Updated 10 September 2026. Implementation is in progress. No playable or photorealistic result is claimed yet.

## First milestone

Capture the actual single-player game window with Windows Graphics Capture, process its D3D11 texture on the RX 7800 XT, and present through a separate Windows companion. A nonactivating overlay should leave mouse and keyboard input with Reforger. F8 must immediately expose the original game; F9 switches processed/passthrough output; F10 exits the companion. Loss of source frames must expose the game automatically.

This route has display-referred RGB including HUD, with capture timestamps. It has no verified depth, motion, normals, material IDs or scene-linear lighting. The Blender feature model remains background research. Model candidates must accept the available RGB input. No game DLL replacement, injection or Steam asset edits are planned.

The initial Windows capture investigation is limited to 45 minutes of implementation and testing. If occluded capture, input routing or presentation fails, retain the runnable viewer and logs and switch to a separate visible viewer while recording that limitation. Do not repeat the failed in-engine screenshot/widget route.

## Measurement contract

Target 2560 × 1440 at 30–60 FPS in local single-player. Record baseline, reduced-cost engine alone, and the same reduction plus enhancement on the same declared gameplay path. Keep texture and geometry identity, cover and vegetation coverage. Start with render scale, shadow quality and screen-space effects as independent cost candidates.

Record game and companion presents, p50/p95/p99 frame intervals, dropped/stale frames, GPU processing and capture-timestamp-to-present-call age. The latter is software pipeline age, not input-to-photon latency. Display/scanout delay and full input latency require separate evidence. Keep recording overhead separate and preserve real elapsed time in clips.

## Work log

1. Existing code and evidence reviewed. Stable Reforger/Workbench are installed. The public engine interface audit found no supported neural resource bridge. No further speculative engine integration is required before testing the Windows route.
2. Windows companion implementation begun on `prototype/playable-companion`. No pretrained candidate has yet been accepted.

## Sources

- [Microsoft: Windows Graphics Capture](https://learn.microsoft.com/en-us/windows/apps/develop/media-authoring-processing/screen-capture)
- [Microsoft: Win32 window capture sample](https://github.com/microsoft/Windows.UI.Composition-Win32-Samples/tree/master/cpp/ScreenCaptureforHWND)
- [PresentMon measurement tool](https://github.com/GameTechDev/PresentMon)
- [Bohemia: startup parameters](https://community.bistudio.com/wiki/Arma_Reforger:Startup_Parameters)

## Live integration milestone · 10 September

The companion captures 1440p game RGB and runs a real native Zero-DCE++ network. A 320 × 180 FP32 curve matches the independent PyTorch checkpoint with maximum error 0.000000075 over 172,800 values. The native backend retains its source, input, checkpoint and output hashes locally. The candidate changes exposure; substantial photorealistic lighting/material improvement is **not established**.

DirectComposition visibly displays the first-person Montignac scene after the initial layered-window swapchain failed to appear. F8 hides the overlay in the retained hotkey log. The source soldier spawns and receives the local player controller; closing Game Master restores its first-person camera. Mouse/keyboard operation through the visible overlay still requires a complete verification. The automated UI driver attempts to activate the nonactivating window and times out; this is retained as a test limitation.

Menu plumbing control: 2,397 frames / 40.012 s, exact RGB inversion, GPU copy/draw median 0.08032 ms. This is **not gameplay performance**. A live neural sample reports roughly 5 ms GPU copy/inference/draw; the complete controlled comparison is pending. The first PresentMon trace records the game but misses the DirectComposition companion, so display latency is not yet resolved. Signed compositor timestamp offsets include negatives and are retained without relabeling them as physical latency.

The unrestricted pretrained candidate over-brightens the source. The bounded candidate preserves source chroma and pixel coordinates and limits its brightness delta. The first hard HUD exclusion created a visible sky seam; the follow-up feathers it. Raw runs and the failed first image remain local.

## Pretrained and reference selection

- [Zero-DCE++ author code and checkpoint](https://github.com/Li-Chongyi/Zero-DCE_extension): 10,561 parameters, RGB-only curve estimation. Downloaded and evaluated on this PC; native FP32 parity passes. Author terms restrict use to academic/noncommercial research; its weights are separate from this repository’s MIT code.
- [HDRNet](https://github.com/google/hdrnet): a photographic retouching candidate using low-resolution bilateral coefficients. Its original TensorFlow/custom operator conversion is deferred until the first loop and measurements are complete.
- [DPIR](https://github.com/cszn/DPIR): an image-restoration alternative. Denoising does not supply missing lighting or physically correct material information; native runtime evaluation remains pending.
- [Poly Haven pavement](https://polyhaven.com/a/pavement_04) and [rural midday lighting reference](https://polyhaven.com/a/rural_asphalt_road): CC0 appearance references for rough surfaces and outdoor light. These are visual references, not pixel-aligned targets for Everon assets. Their identity must not replace the game’s own roads, walls or foliage.
