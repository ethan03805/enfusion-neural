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

The [RGB depth motion check](model-evaluation.md#rgb-depth-in-motion) retains all 600 frames of a ten-second walking/turning segment. Coarse motion diagnostics pass, including the reserved final three seconds, but openings and thin cover remain unreliable. The 448 × 252 DirectML model costs 14.93 ms median / 15.88 ms p95; CPU preprocessing adds 30.16 ms median. This offline workflow is unsuitable for live integration. Contact sheets and native-size keys were reviewed; full real-time playback inspection remains incomplete.

The subsequent [native sky control](model-evaluation.md#native-illumination-control) accepts the parameter assignment but produces no useful visible lighting change. Roof differences are comparable to the reset control. The 12.8-minute investigation is closed with both validated addons, logs and all captures retained; no target or preset is accepted.

Engine actions verify walking and camera turning under continuous processing. Physical WASD/mouse interaction, extended movement, interiors, scopes, adverse weather, HDR and semantic fallback remain unverified. Generic CC0 material references are retained but do not match the native assets or provide aligned training targets. Empty moving-path ETW/DXGI display results remain explicit limitations; unchanged probes are closed.

Earlier [appearance evaluations](model-evaluation.md) retain failed photo grades, costly restoration, native texture-copy timeout and the 16–25 ms CPU collision grid. The native roof scalar can be changed and restored, but both moderate candidates lose slate contrast in the reserved view. No replacement preset or improved training target is accepted.

Next: evaluate one compact pretrained model that predicts local and global corrections from the available RGB. Require a visible appearance benefit and measured RX 7800 XT cost before live work. The [roadmap](roadmap.md) fixes the next bound and acceptance gates. Blender studies remain [background research](research-history.md).
