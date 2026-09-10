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

The latest [IAT RGB evaluation](model-evaluation.md#iat-rgb-correction) is rejected after 14.1 minutes. Its unchanged author checkpoint passes CPU/DirectML parity but costs 27.66–29.46 ms per synchronized call at 960 × 540 before composition or game rendering. Raw outputs lose shade detail; the fixed bounded version gives insufficient appearance gain and exposes mask seams. All failures and code are retained. The playable build is unchanged.

Earlier [depth motion](model-evaluation.md#rgb-depth-in-motion) and [native sky control](model-evaluation.md#native-illumination-control) trials also remain closed. Coarse inferred depth cannot support reliable relighting of openings and thin cover; the selected native sky assignment gives no useful visible response. Neither supplies an accepted appearance target.

Engine actions verify walking and camera turning under continuous processing. Physical WASD/mouse interaction, extended movement, interiors, scopes, adverse weather, HDR and semantic fallback remain unverified. Generic CC0 material references are retained but do not match the native assets or provide aligned training targets. Empty moving-path ETW/DXGI display results remain explicit limitations; unchanged probes are closed.

Earlier [appearance evaluations](model-evaluation.md) retain failed photo grades, costly restoration, native texture-copy timeout and the 16–25 ms CPU collision grid. The native roof scalar can be changed and restored, but both moderate candidates lose slate contrast in the reserved view. No replacement preset or improved training target is accepted.

Next: measure sustained movement on a repeated, passable street route with standard, reduced and enhanced passes. This closes a runtime acceptance gap; it does not resolve the missing photorealistic appearance model or aligned reference target. The [roadmap](roadmap.md) fixes the bound and acceptance gates. Blender studies remain [background research](research-history.md).
