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

The latest [RGB depth evaluation](model-evaluation.md#rgb-depth-feasibility) finds a possible coarse input: Depth Anything V2 Small runs in 10.2–11.0 ms at 462 × 252 on DirectML. A larger graph costs 24.2 ms; the single FP16 conversion fails the no-CPU-fallback requirement. Combined street depth checks pass, but building-only ordering is weaker and openings flatten out. Surface relighting is not accepted. These are offline model costs, not complete application performance.

Engine actions verify walking and camera turning under continuous processing. Physical WASD/mouse interaction, extended movement, interiors, scopes, adverse weather, HDR and semantic fallback remain unverified. Generic CC0 material references are retained but do not match the native assets or provide aligned training targets. Empty moving-path ETW/DXGI display results remain explicit limitations; unchanged probes are closed.

Earlier [appearance evaluations](model-evaluation.md) retain failed photo grades, costly restoration, native texture-copy timeout and the 16–25 ms CPU collision grid. The native roof scalar can be changed and restored, but both moderate candidates lose slate contrast in the reserved view. No replacement preset or improved training target is accepted.

Next: check the smaller depth model on a bounded retained gameplay segment for motion stability and HUD interference before any lighting effect. Inferred relative depth is not an engine buffer or metric geometry. The [roadmap](roadmap.md) gives the remaining gates. Blender studies remain [background research](research-history.md).
