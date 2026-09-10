# Remaining acceptance

Target: faithful photorealistic appearance at 2560 × 1440 and 30–60 FPS on the RX 7800 XT in local single-player.

| Area | Established | Required next |
| --- | --- | --- |
| Live loop | Actual game capture → GPU neural pass → visible companion; source bypass, separate viewer and ten-minute mostly stationary runtime check | Physical WASD/mouse check, menu/focus/scope transitions and extended movement |
| Budget | Runtime-verified town baseline, individual reductions and enhancement; separate recording overhead; second matched 74-metre street comparison | Repeated passes and denser vegetation/interior coverage; displayed-frame telemetry remains a specific external limitation |
| Latency | 895-frame software display join; moving-path processing age | Moving-path capture-to-display evidence and physical input-to-photon test |
| Model | Native Zero-DCE++ parity; appearance models and native material controls evaluated; coarse RGB depth feasibility measured | Demonstrated material/lighting gain; another photo grade or depth map alone does not satisfy this gate |
| Fidelity | Fixed source coordinates, bounded brightness and source fallback; normal-speed paths | Visibility/temporal acceptance around cover, openings, thin foliage and darker environments |
| Delivery | Launcher, companion, addon, attribution, normal-speed capture and measured evidence | Finish the explicit acceptance gaps before calling this the requested photorealistic prototype |

The next task is a **30-minute offline motion check** of the smaller Depth Anything V2 graph on retained gameplay RGB. Select one fixed 10-second walking/turning segment before processing, with its last three seconds reserved. Keep source timestamps, use fixed visualization normalization, and retain every prediction. Record actual input shape, timing and CPU parity if the static export shape changes for 1440p captures. Inspect HUD contamination, opening/pole boundaries and frame-to-frame depth changes. Any correspondence metric must reject occlusions and report coverage. Do not tune on the reserved segment or add surface lighting to hide a failed depth result.

Only after that check can a separate bounded appearance experiment be proposed. It must name a usable photographic or native reference, preserve the existing asset, specify source fallback, and show a visible material/lighting gain before live integration. Depth estimation alone does not meet the appearance objective. Live integration must then repeat complete game/companion cadence and latency measurements; model-call time is insufficient.

Closed routes remain available in the [appearance evidence](model-evaluation.md), [playable work log](playable.md) and [decisions](decisions.md):

| Route | Reason to keep it closed |
| --- | --- |
| Unchanged renderer bridge, screenshot/widget and Blender investigations | No verified live surface-buffer path; Blender is background research |
| Moving-path ETW / DXGI statistics probes | Empty or zero display counters, including the single DwmFlush variant |
| Native texture copying | Timed out without output; material identity lookup still works |
| Per-frame collision grid | 16–25 ms CPU and unresolved visible-surface correspondence; offline use remains valid |
| Rejected photo grades and SPAN live integration | Visibility/identity failure, inadequate appearance gain or excessive cost |
| Roof roughness 0.4 / 0.7 presets | Pale sheen and reduced slate contrast in the reserved view; retain the working change/reset control |
| Depth 392 FP32 / single FP16 graph | FP32 over budget; FP16 session requires CPU-assigned operations |

Do not retry these unchanged routes without new feasibility evidence. Preserve all failures, including fence-colliding paths, the world-loading crash and failed conversions. Physical input verification remains pending user interaction; it does not prevent bounded offline work.

[Current status](status.md) · [Build and comparison](playable.md) · [Research archive](research-history.md)
