# Architecture

The live path is **Reforger window → Windows Graphics Capture → D3D11 neural processing → companion window**. It runs beside an isolated local single-player addon. The Steam installation and original user profile remain unchanged.

## Live frame path

Windows supplies a BGRA8 display-referred RGB texture, including HUD, and a compositor timestamp. Depth, motion vectors, normals, material IDs and scene-linear lighting are unavailable through the verified interface. Model selection must respect that limit.

The companion selects the RX 7800 XT through DXGI, keeps capture, inference and drawing on D3D11, and presents a normal HWND flip-discard swapchain. The queue keeps the newest source frame. GPU timestamps cover copy, inference and drawing; separate PresentMon traces count application presents. Snapshot readback and video recording are explicit diagnostic costs.

Zero-DCE++ predicts three exposure curves at 320 × 180 in FP32. Seven depthwise/pointwise convolution blocks reproduce the author's 10,561 parameters. The original eight curve iterations are composed at output resolution, converted to bounded luminance gain and blended at strength 0.35. Source pixel positions and chroma are retained. This changes exposure; it does not reconstruct material detail or lighting.

## Controls and failure behavior

F8 hides the overlay and exposes the source. F9 switches the companion between identity and the selected enhancement. F10 closes the companion. Loss of focus, minimization, old capture frames or a presentation timeout also hides the overlay. Invalid neural curves fall back to source pixels.

The overlay is nonactivating and disabled for normal window input. Automated engine actions prove live movement through the displayed scene; complete physical WASD/mouse routing is still awaiting verification. A separate ordinary viewer is available. These limits are tracked in [current status](status.md).

The shader protects near-black and highlight regions, feathers fixed HUD margins and protects the crosshair. The downloadable build also caps positive common RGB gain by source-channel headroom, using a 254/255 ceiling before feathering. This avoids new endpoints in the complete 600-frame offline replay, fixed saturation fixtures and the current live snapshot. The guarded release passes live replay parity, controls and application-cadence checks. These are numerical guards, not semantic masks or a reconstruction-failure detector. No temporal image history is used, so there is no history ghosting; exposure variation and source aliasing still require movement review.

## Components

| Component | Responsibility |
| --- | --- |
| `adapters/playable/` | Isolated addon, local soldier, fixed weather, optional repeatable walking/turning path, runtime settings readback |
| `scripts/launch_playable.py` | Private addon/profile preparation and game launch |
| `scripts/play.py` | Free-play launch, companion and controls |
| `native/companion.cpp` | WGC capture, overlay/viewer, shader composition, fallback, timing and snapshots |
| `native/curve_network.h` | Native pretrained FP32 network |
| `native/dce_replay.cpp` | Offline 1440p replay of the same network and extracted shader, with full readback and curve dumps; no capture, window or Present |
| `enr/exposure_guard.py` | Independent CPU reference for constant-curve saturation and fallback fixtures; excluded from the live frame path |
| `scripts/prepare_pretrained.py` | Pinned downloads, hashes and native tensor export |
| `scripts/benchmark_playable.py` | Serialized owned sessions, settings guards, PresentMon and optional recording |
| `scripts/analyze_playable.py` | Fixed-path game/companion cadence, processing time and available latency joins |
| `scripts/package_playable.py` | Runnable package with source, weights, attribution and hashes |

## Retained research

The standalone D3D12 backend, original CPU models and independent numerical references remain available. Their dispatch timings exclude game capture and display. The [Blender lighting studies](lighting-study.md), [motion studies](lighting-motion.md), [material fixture](material-room.md) and [research history](research-history.md) retain earlier findings.

The unsupported screenshot/widget return and in-engine renderer-resource bridge are closed for this iteration. They provide no live input buffers to the current model. Changes to a GPU graph must continue to pass its independent CPU reference.

The paired replay matches a saved native snapshot exactly, including curves and RGB8 composition. The independent CPU network agrees within 1.79 × 10⁻⁷; the CPU full compositor misses its predeclared 0.02-code mean tolerance at 0.033434 codes. Preserve that unresolved composition bias instead of describing native self-reproduction as independent CPU composition parity. The source-only flow diagnostic measures added luminance variation with exclusions; it is not a semantic fidelity or full perceptual test.

The supported world API exposes collision traces. The completed 64 × 36 grid costs 16–25 ms CPU and has unresolved visible-surface correspondence. It remains an offline diagnostic; per-frame integration is closed.

Depth Anything V2 Small infers coarse relative depth from RGB on DirectML. The 600-frame offline motion check costs 14.93 ms median / 15.88 ms p95 at 448 × 252, plus 30.16 ms median CPU preprocessing. Coarse diagnostics pass, while openings, thin detail and building depth remain insufficient for surface relighting. No live integration, metric geometry, normal buffer or temporal history is established. See the [depth evaluation](model-evaluation.md#rgb-depth-in-motion).
