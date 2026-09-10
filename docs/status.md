# Current status

Updated 10 September 2026. The [runnable Windows build](playable.md) captures and processes local Reforger gameplay at **2560 × 1440** on RX 7800 XT through an isolated addon. **F8** exposes the source, **F9** toggles enhancement, and **F10** exits the companion. The launcher requires Python 3; inference does not.

**Substantial photorealistic material and lighting improvement remains unfinished.** The current Zero-DCE++ pass makes a modest exposure change while retaining source pixel positions. Captured RGB with HUD is the only verified live model input.

| Measurement | Established result | Limit |
| --- | --- | --- |
| Controlled town, standard / reduced / enhanced | 88.0 / 104.7 / 88.1 game presents/s; companion 60.7 | Companion p95 / p99 intervals 30.4 / 32.1 ms; maximum 41.5 ms |
| GPU copy, network and draw | 3.44 ms median / 6.11 ms p95 in town | Excludes complete game and display latency |
| Earlier 895-frame software display join | 12.61 ms median / 18.12 ms p95 capture-to-reported-display | Separate scene; moving-path display and physical input latency remain unavailable |
| Ten-minute operation | 36,654 processed frames, no recorded crash/hide/timeout; companion 61.1 presents/s | Mostly stationary after the initial walk; one 52.9 ms interval |
| Recorded, matched 74-metre street | 70.9 / 84.9 / 69.5 game presents/s; companion 60.0 | Retains standard pass's 295 ms stall; tree-lined street, not dense forest |

The [appearance evaluations](model-evaluation.md) retain every rejected candidate. 3DLUT and DeepLPF lose shaded detail or give insufficient grading improvement; REGEN changes identity and costs 53–54 ms; SPAN improves synthetic restoration but costs 35–72 ms and adds no demonstrated material/lighting gain. Native inspection verifies 13 material defaults on an existing slate-roof building, but texture copying times out without outputs. Two collision-grid views now identify broad geometry at 16–25 ms CPU cost, with unresolved thin features and some zero normals. That grid is rejected as a live input. These investigations leave the working build unchanged.

Engine actions verify walking and camera turning under continuous processing. Physical WASD/mouse interaction, extended movement, interiors, scopes, adverse weather, HDR and semantic fallback remain unverified. Generic CC0 material references are retained but do not match the native assets or provide aligned training targets. Empty moving-path ETW/DXGI display results remain explicit limitations; unchanged probes are closed.

Next: test supported runtime parameter changes on the identified roof material, with unchanged textures and a source/change/reset control. This tests whether an identity-preserving appearance reference can be authored; it is not yet a photorealistic target or neural result. The [roadmap](roadmap.md) gives the bound and remaining acceptance gates. Blender studies remain [background research](research-history.md).
