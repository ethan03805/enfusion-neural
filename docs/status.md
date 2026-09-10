# Current status

Updated 10 September 2026. The active objective is a playable Windows companion and isolated Reforger addon at **2560 × 1440, 30–60 FPS**. This supersedes the earlier 20 FPS research floor.

The [playable prototype log](playable.md) records implementation and current evidence. Windows Graphics Capture now feeds a native GPU neural pass and a visible companion over the local first-person game. The Blender studies remain background research.

The first pretrained Zero-DCE++ pass takes roughly 5 ms of GPU copy/inference/draw at 2560 × 1440, with curve prediction at 320 × 180. An initial 895-frame timestamp join reports 12.61 ms median and 18.12 ms p95 from capture to reported display. This is software latency, not input-to-photon. F8 bypass works. Physical mouse/keyboard operation through the visible overlay remains incompletely verified.

Engine input actions now move the controlled soldier through the town for 20 seconds and turn for 10 seconds. The corrected standard preset reports **87.96 game presents/s**, **13.43 ms p95** intervals and **11.22 ms median GPU activity**. The 75%-scale/FSR1 case reaches **97.15 presents/s** but includes three intervals over 33.3 ms; its display/GPU trace is unavailable. The earlier 114.70 result used engine defaults because the private settings path was wrong. Runtime readback now guards the corrected profiles.

The current candidate adjusts exposure and retains source pixel positions. A second photographic model was evaluated and its unrestricted output rejected for clipping foliage shadows. Both outcomes are visible in the work log. **Substantial photorealistic material/lighting improvement has not been achieved.** No current result meets the complete objective.

Next acceptance: finish input verification, compare the same path with each rendering reduction and enhancement, publish unretimed gameplay, and package the runnable companion and addon.

Previous numerical results and failure records are retained in the [research history](research-history.md). Do not rerun unchanged failed screenshot/widget probes or frozen Blender studies. No Bohemia message has been sent.
