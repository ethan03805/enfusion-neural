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
