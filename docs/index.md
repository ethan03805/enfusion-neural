# Enfusion Neural

A playable neural appearance prototype for Arma Reforger, using an isolated addon and a Windows companion. Target: **2560 × 1440 at 30–60 FPS on RX 7800 XT in local single-player**.

The [runnable Windows build and normal-speed gameplay comparison](playable.md) are available. Continuous capture, GPU processing, visible presentation and F8 bypass work. In the town path, the game runs at 88.1 presents/s with reduced settings plus enhancement, and the companion produces 60.7 presents/s. Frame pacing and latency limits are documented separately.

**Substantial photorealistic material and lighting improvement has not been achieved.** The current network makes a modest exposure change. Physical mouse/keyboard routing and broader visibility/stability acceptance remain unfinished.

| Read | Purpose |
| --- | --- |
| [Playable prototype](playable.md) | Current build, controls, measurements and work log |
| [Current status](status.md) | What works and the next acceptance gate |
| [Objectives](vision.md) | Preserve identity, openings, cover and visibility |
| [Architecture](architecture.md) | Live companion boundary and retained offline backend |
| [Arma scenes](arma-scenes.md) | Existing town, interior, foliage and entity fixtures |
| [Comparisons](comparisons.md) | Earlier labeled image and retimed research comparisons |
| [Research history](research-history.md) | Prior Blender and engine-interface experiments |

The previous Blender lighting studies and standalone neural timings remain background research. The live companion selects its model around RGB frames that Windows actually supplies.
