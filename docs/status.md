# Current status

Updated 10 September 2026. A runnable Windows companion now captures and processes local Reforger gameplay at **2560 × 1440** using an isolated addon. It has an F8 source bypass, F9 enhancement toggle and F10 exit. The live network runs on the RX 7800 XT; the launcher needs Python 3, but inference does not.

The controlled town path measures **88.0 game presents/s** with standard settings, **104.7** with the combined rendering reduction, and **88.1** with that reduction plus neural processing. The companion produces **60.7 presents/s**, with **30.4 ms p95** and **32.1 ms p99** intervals. Twelve intervals exceed 33.3 ms; the maximum is 41.5 ms. This is a short measured sample, not a locked-60 guarantee.

GPU copy, inference and drawing take **3.44 ms median / 6.11 ms p95** in that path. The earlier 895-frame display join measures **12.61 ms median / 18.12 ms p95** capture-to-reported-display latency. Moving-path display traces remain unavailable after a bounded retry. Two subsequent DXGI-counter probes also return only zero display counters, including the documented `DwmFlush` variation; that route is closed with code and evidence retained. None of these measurements is physical input-to-photon latency.

A separate **ten-minute runtime check** completes with 36,654 processed frames and no crash, recorded hide or presentation timeout. The game averages 89.3 presents/s and the companion 61.1, with 29.7 / 31.9 ms p95 / p99 intervals and one 52.9 ms interval. Most of this run is stationary after the existing walking segment; extended movement and manual interaction remain unverified.

A second **matched street comparison** now replaces the colliding foliage route in the main gameplay view. All three passes travel about 74 metres, with sampled camera differences below the declared 0.5-metre limit. With recording enabled, standard / reduced / enhanced game throughput is 70.9 / 84.9 / 69.5 presents/s; the companion averages 60.0. The standard pass's 295 ms stall is retained. This covers a tree-lined street, not dense forest; the failed fence pilots and one world-loading crash remain documented.

**The complete appearance objective is unfinished.** Zero-DCE++ makes a modest exposure change and preserves source pixel positions. A second photographic model was evaluated and rejected for clipping foliage shadows. Neither establishes substantial photorealistic material or lighting improvement. The current input is RGB with HUD; no verified depth, normals, motion or material buffers are available.

Two more [appearance candidates](model-evaluation.md) have now been evaluated on the same three town/foliage frames. REGEN executes correctly on RX 7800 XT DirectML but takes 53–54 ms at 960 × 544, alters roof color and adds sky artifacts. DeepLPF clips shaded detail; its protected version avoids new black clipping but remains a color/contrast change. Both integration attempts are closed with code, raw outputs and reproducible hashes retained. Neither earns a photorealism or temporal acceptance claim.

Engine actions verify a walking soldier and camera turn under continuous processing. Physical WASD/mouse operation through the overlay still needs a user check. Extended movement, interiors, scopes, adverse weather, HDR and semantic failure detection are outside accepted coverage. Three CC0 road/roof/bark reference sets are retained, but their patterns differ from the game; they are not aligned training targets.

See the [playable prototype](playable.md) for the build, normal-speed comparisons, complete measurements and retained failures. The [roadmap](roadmap.md) identifies the remaining acceptance gates. Blender work remains [background research](research-history.md).
