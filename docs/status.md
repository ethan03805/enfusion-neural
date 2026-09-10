# Current status

Updated 10 September 2026. The [runnable Windows build](playable.md) captures and processes local Reforger gameplay at **2560 × 1440** on RX 7800 XT through an isolated addon. **F8** exposes the source, **F9** toggles enhancement, and **F10** exits the companion. The launcher requires Python 3; inference does not.

**Substantial photorealistic material and lighting improvement remains unfinished.** Zero-DCE++ makes a modest exposure change while retaining source pixel positions. Captured RGB with HUD is the only verified live model input.

| Measurement | Established result | Limit |
| --- | --- | --- |
| Latest recorded 180-second repeated route | 69.99 / 85.72 / 72.03 game presents/s for standard / reduced / enhanced; companion 60.21 | Companion p95 / p99 intervals 30.57 / 32.74 ms; maximum 49.22 ms, 85 intervals above 33.3 ms |
| Sustained movement | 156 moving seconds, 590–591 metres per pass; maximum route difference 0.78 m / 1.46° | Engine actions; sampled visual review, no physical input claim |
| GPU copy, network and draw on that route | 3.53 ms median / 6.28 ms p95 | Capture-to-Present age 6.58 / 14.14 ms; excludes panel/input latency |
| Earlier unrecorded town | 88.0 / 104.7 / 88.1 game presents/s; companion 60.7 | Different route/window; recording cost is not inferred by subtracting these results |
| Earlier 895-frame software display join | 12.61 ms median / 18.12 ms p95 capture-to-reported-display | Separate scene; moving-path display and physical input latency remain unavailable |
| Ten-minute operation | 36,654 processed frames, no recorded crash/hide/timeout | Mostly stationary after the initial walk; one 52.9 ms interval |

The new [184-second unretimed comparison](playable.md#three-minutes-of-repeated-movement) shows four out-and-back street cycles. All three final passes retain game focus, and the companion logs no fallback or timeout. Review covers 552 chronological one-second samples and 24 native-size keys. Buildings, openings, barriers and vegetation remain recognizable; peripheral blur and fine-detail aliasing persist. These samples do not establish frame-to-frame flicker or target visibility. The live measurements finish within the declared hour; review and evidence preparation close at **66.0 minutes**, exceeding the bound. Failures and original attempts remain in the evidence.

The [appearance evaluations](model-evaluation.md) retain rejected photo grades, costly restoration, native material/sky trials and coarse RGB depth. One [synthetic appearance proposal](model-evaluation.md#synthetic-appearance-target) adds stronger material shading but redraws roof/road texture and lettering, and returns a smaller canvas. It is rejected after 3.5 minutes, with the unchanged output retained. Synthetic art direction and generic CC0 material references do not establish aligned photographic ground truth. No replacement model or improved training target is accepted.

Physical WASD/mouse interaction, interiors, scopes, adverse weather, HDR and semantic fallback remain unverified. Empty moving-path ETW/DXGI display results remain explicit limitations; unchanged probes are closed. The download is unchanged and remains usable for the established exposure pipeline.

Next: a bounded paired-frame temporal diagnostic of the existing DCE pass, using the same captured RGB for source and processed output. It must isolate enhancement changes from game motion and retain its correspondence limits. The missing appearance target remains a separate blocker; this check cannot satisfy photorealism. The [roadmap](roadmap.md) fixes the next check. Blender studies remain [background research](research-history.md).
