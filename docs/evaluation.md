# Evaluation

An attractive screenshot is insufficient. Evaluate scene fidelity, temporal behavior and complete frame cost separately, using the same scenes and recorded configuration.

## Current executable checks

The benchmark compares every output pixel to independent CPU inference with a maximum RGB tolerance of one 8-bit code value and exact alpha. It records all 100 warmed dispatch samples, the selected hardware adapter, model/input hashes, dimensions and separate upload, readback and file processing costs.

The learning evaluation holds out entire procedural scene seeds, not random neighboring patches from the same image. Report all four fixed test scenes, including regressions. PSNR and MSE here measure reconstruction under a known degradation, not photorealism, visibility preservation or temporal quality.

## Appearance acceptance suite

Create controlled test sequences for vegetation, thin geometry, characters, faces, uniforms, vehicles, scopes, reticles, text, interiors, dusk and rapidly changing exposure. Include concealed targets and empty locations. Use slow pans, fast motion, disocclusion and camera cuts. Record native and disabled/identity baselines with the same settings.

- Geometry: inspect silhouette displacement and extra or missing objects. A provisional one-pixel output boundary tolerance is a test target, not a guarantee.
- Identity: compare faces, insignia, writing, clothing and material appearance across views. Reject invented or rewritten detail even when it improves an aesthetic score.
- Visibility: concealed targets stay concealed; visible targets stay present. Blinded recognition tests supplement image metrics.
- HUD and reticles: require exact equality at the protected composition boundary once that boundary exists. Alpha preservation alone is not HUD protection.
- Temporal stability: inspect raw clips, motion-aligned residuals and disocclusions. Camera motion alone cannot account for animated foliage or characters.
- Lighting: use aligned references and known exposure/transfer conventions. Avoid a metric that rewards merely brighter or sharper output.

No such appearance or temporal suite has passed yet. Do not report the v0 model as production ready.

## Performance protocol

The product floor is 20 FPS at 1440p on RX 7800 XT: 50 ms for the whole frame. Begin with game-only measurements, then identity integration, then neural integration. Run three separated trials per scene after warmup, keep raw frame samples and record p50/p95/p99/max, input-to-present latency, peak memory, DXGI budget and dropped frames. Perform a 30-minute soak after shorter checks pass.

The existing 10-warmup/100-dispatch benchmark is a microbenchmark, not this protocol. The provisional neural allowance is 10 ms at p95 and 1 GiB added memory, subject to actual game headroom. Test 720p, 1080p, 1440p, 4K, ultrawide and odd dimensions; correctness support and acceptable performance are separate claims.
