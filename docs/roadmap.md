# Remaining acceptance

Target: faithful photorealistic appearance at 2560 × 1440 and 30–60 FPS on the RX 7800 XT in local single-player.

| Area | Established | Required next |
| --- | --- | --- |
| Live loop | Actual game capture → GPU neural pass → visible companion; source bypass, separate viewer, three-minute repeated movement and ten-minute mostly stationary runtime check | Physical WASD/mouse check and menu/focus/scope transitions |
| Budget | Runtime-verified town baseline, individual reductions and enhancement; separate recording overhead; matched 74-metre street and 180-second repeated-route comparisons | Repeated passes and denser vegetation/interior coverage; displayed-frame telemetry remains a specific external limitation |
| Latency | 895-frame software display join; moving-path processing age | Moving-path capture-to-display evidence and physical input-to-photon test |
| Model | Native Zero-DCE++ parity; appearance models and native material controls evaluated; coarse RGB depth feasibility measured | Demonstrated material/lighting gain; another photo grade or depth map alone does not satisfy this gate |
| Fidelity | Fixed source coordinates, bounded brightness and source fallback; normal-speed paths | Visibility/temporal acceptance around cover, openings, thin foliage and darker environments |
| Delivery | Launcher, companion, addon, attribution, normal-speed capture and measured evidence | Finish the explicit acceptance gaps before calling this the requested photorealistic prototype |

The IAT evaluation closes after 14.1 minutes: independent CPU parity passes, but synchronized FP32 calls exceed the 10 ms p95 ceiling and raw outputs lose visibility. The fixed bounded version gives no substantial appearance benefit and creates hard mask seams. Preserve the rejected outputs. Do not extend this into another sequence of generic photo-grade searches or optimize a candidate that already fails appearance.

The sustained route comparison passes its declared movement, spatial and direction gates after one measurement amendment to 10 Hz camera logging. Retain the original sparse-direction failure, zero-frame enhancement attempt and intervened standard pass. The final triple has unchanged route and thresholds. Review/evidence closure exceeds the original hour at 66.0 minutes; no further gameplay trials extend that experiment. The [comparison](playable.md#three-minutes-of-repeated-movement) publishes all 184 seconds at original elapsed speed and states its sampled-review limits.

Next is a **20-minute offline appearance-target feasibility check**, using one already captured street frame with roof, facade, openings, barriers and foliage. Before generation, freeze the source hash and landmarks covering roof silhouette, door/window corners, thin poles, barrier gaps, text and shadow boundaries. Request one source-conditioned lighting/material proposal through the built-in image tool, preserving camera, weather, material identity and every gameplay object. No prompt search or second candidate is part of this check. Keep the source and raw proposal unchanged and label the proposal **synthetic art direction, not photographic ground truth**.

Inspect the full proposal and fixed landmarks. Reject moved boundaries, changed openings/cover, invented texture or text, different weather/material identity, lost shade visibility, or an effect that is merely another brightness grade. Publish the decision and visible failures. Do not integrate the generative model into gameplay or train from a rejected target. If a proposal passes, the separate next step must test whether a compact deterministic, source-coordinate correction can reproduce the useful low-frequency change while retaining detail and temporal stability. A good still image alone cannot pass the playable acceptance gate.

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
| Depth motion graph in its current Python workflow | 15.88 ms p95 model call plus 30.16 ms median CPU preprocessing; no demonstrated appearance benefit or reliable thin geometry |
| Cached sky material, SkyIntensityLV 8 → 8.5 | Assignment succeeds without a useful visible response; no accepted lighting target |
| IAT exposure checkpoint at the fixed RGB contract | 28–30 ms synchronized calls, lost shade detail; bounded output adds mask seams and insufficient appearance gain |

Do not retry these unchanged routes without new feasibility evidence. Preserve all failures, including fence-colliding paths, the world-loading crash and failed conversions. Physical input verification remains pending user interaction; it does not prevent bounded offline work.

[Current status](status.md) · [Build and comparison](playable.md) · [Research archive](research-history.md)
