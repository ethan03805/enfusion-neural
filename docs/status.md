# Current status

Updated 10 September 2026. The active objective is a playable Windows companion and isolated Reforger addon at **2560 × 1440, 30–60 FPS**. This supersedes the earlier 20 FPS research floor.

The [playable prototype log](playable.md) records implementation and current evidence. The existing engine interface investigation is closed for this iteration; Windows window capture is the next route. The Blender studies remain background research.

Current measured capability: offline D3D12 inference and Workbench image capture. Live capture, presentation, bypass, added latency, pretrained appearance quality and complete-game performance are pending. No current result meets the playable objective.

Next acceptance: an actual single-player game stays controllable behind continuous GPU capture/processing/presentation, with an immediate bypass, automatic stale-frame fallback and retained timestamp/pacing logs.

Previous numerical results and failure records are retained in the [research history](research-history.md). Do not rerun unchanged failed screenshot/widget probes or frozen Blender studies. No Bohemia message has been sent.
