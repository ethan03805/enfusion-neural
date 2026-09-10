# Objectives

The research objective is to improve lighting and material appearance while preserving scene geometry, identity and visibility. The initial complete-frame target is 1440p at 30–60 FPS on a declared test configuration. Evaluation must also cover other resolutions and quality settings.

## Fidelity contract

Improve illumination, shading continuity and the appearance of surfaces. Keep faces, clothing, terrain, object placement, text, weapons and silhouettes consistent with the source. A material should not acquire a different identity because a model thinks it looks more photographic.

No prompt-driven restyling, fabricated fine detail or frame-by-frame generative redraw belongs in the default path. This is a research direction, not a guarantee that a small residual model cannot produce artifacts. Changes require measured spatial and temporal checks.

Concealed targets must stay concealed. Foliage, fences and thin wires are part of the scene. A still image that looks impressive but changes visibility or flickers in motion fails the goal.

## Initial evaluation targets

| Quantity | Initial target or constraint |
| --- | --- |
| Output | 2560 × 1440; support other valid dimensions |
| Playable floor | 30–60 FPS, 16.7–33.3 ms per complete frame |
| Priority | Scene fidelity, then reduced cost without losing fidelity |
| Provisional neural allocation | Up to 10 ms at p95, revised after the real engine baseline |
| Provisional added GPU memory | At most 1 GiB; measure actual budget and peak use |
| Development | Local experiments; paid training requires a separate budget |

The 10 ms allowance is a planning ceiling, not an achieved budget or entitlement. If the game already takes 33.3 ms, enhancement must reduce other costs or use a different profile. Averaging 30 FPS while producing large stalls is insufficient. Measure p95/p99 frame times, input latency and a long run.

## Appearance model direction

Start with aligned, licensed references and a compact deterministic residual network. Explore lighting and material correction at lower spatial frequencies before learning new high-frequency detail. Add temporal conditioning only with a trustworthy motion and exposure contract. Depth, normals and material buffers would allow more informed processing, but they are not yet available through a verified integration.

Ordinary game screenshots are observations, not ground-truth photorealistic targets. Photograph-to-game translation without alignment can change geometry and identity. Build original controlled scenes or obtain authorized paired reference data; document what each pair represents.

The v0 reconstruction CNN is an engineering baseline. It will remain available even when a more capable appearance model replaces it. No quality claim transfers automatically from one model or scene to another.
