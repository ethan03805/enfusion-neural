# Active roadmap

Target: 2560 × 1440 at 30–60 FPS on the RX 7800 XT, local single-player.

| Milestone | Current evidence | Acceptance still needed |
| --- | --- | --- |
| Continuous game capture and GPU processing | WGC → native D3D11 Zero-DCE++ → visible HWND companion | Physical input verification; resilience during menu and focus changes |
| Bypass and latency | F8 exposes source; software capture-to-display timestamp join | Controlled path latency and pacing; distinguish physical input latency |
| Isolated single-player addon | Controlled soldier, fixed weather, engine input walking and heading sweep | Additional foliage and interior paths |
| Render budget | Engine readback verifies corrected private profiles | Baseline, separate reductions and enhancement without ETW loss |
| Appearance model | Zero-DCE++ native parity; Image-Adaptive-3DLUT CPU evaluation | Photorealistic material/lighting gains, visibility and movement acceptance |
| Delivery | Launcher and measurement scripts | Runnable package, reviewed unretimed comparisons and final report |

The [current status](status.md) and [playable work log](playable.md) contain current evidence and failures. The [research history](research-history.md) retains earlier numerical and synthetic studies. Those studies are background; the unsupported in-engine screenshot/widget and renderer-bridge routes are closed for this iteration.
