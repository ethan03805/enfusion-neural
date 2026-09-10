# Enfusion Neural

A playable neural appearance prototype for Arma Reforger, using an isolated addon and a Windows companion. Target: **2560 × 1440 at 30–60 FPS on RX 7800 XT in local single-player**.

Implementation is in progress. The first task is continuous gameplay capture, GPU processing and display with a working bypass and measured added latency. A substantial improvement to materials and lighting has not yet been demonstrated.

| Read | Purpose |
| --- | --- |
| [Playable prototype](playable.md) | Current build, controls, measurements and work log |
| [Current status](status.md) | What works and the next acceptance gate |
| [Objectives](vision.md) | Preserve identity, openings, cover and visibility |
| [Architecture](architecture.md) | Live companion boundary and retained offline backend |
| [Arma scenes](arma-scenes.md) | Existing town, interior, foliage and entity fixtures |
| [Comparisons](comparisons.md) | Earlier labeled image and retimed research comparisons |
| [Research history](research-history.md) | Prior Blender and engine-interface experiments |

The previous Blender lighting studies and standalone neural timings are research evidence. They do not establish live-game visual quality or complete application performance. The companion will select its model around RGB frames that Windows actually supplies.
