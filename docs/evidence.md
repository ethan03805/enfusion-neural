# Evidence

Measured locally on 8 September 2026. The results establish an offline neural path on RX 7800 XT. They do not establish photorealism or live game performance.

## Neural GPU execution

| Input | Dimensions | Dispatch p50 | Dispatch p95 | CPU comparison |
| --- | --- | --- | --- | --- |
| Procedural fixture | 2560 × 1440 | 0.11816 ms | 0.17368 ms | Pass; max RGB error 1, alpha exact |
| Arland Workbench capture | 1839 × 947 | 0.05664 ms | 0.07968 ms | Pass; max RGB error 1, alpha exact |

Each run contains ten warmups and 100 measured dispatches on the same buffers, including a UAV barrier in each dispatch interval. Selected hardware: **AMD Radeon RX 7800 XT**. Native FP32 HLSL executes the trained 251-parameter model. There is no inference runtime or CPU operator fallback in this shader path.

The file pipeline took **764.74 ms** for the 1440p run and **690.43 ms** for Arland. Each value includes startup, shader compilation, 110 dispatches and output export, and excludes the separate CPU reference check. It is not per-frame latency. The current file pipeline is not a playable renderer.

[1440p raw samples and manifest](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/gpu-1440p.json) · [Arland raw samples and manifest](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/gpu-arland.json)

Correctness also passed for random RGBA inputs at 1 × 1, 1 × 17, 31 × 1, 127 × 65, 1920 × 1080 and 3840 × 2160. Each comparison checked every RGB value and exact random alpha. These smoke checks prove numerical behavior at those sizes, not acceptable frame times on other GPUs.

## Learning result

Training fits all network weights on the local CPU with seed 7, 1,200 Adam steps and original procedural data. Train scene seeds are 0–11; validation scenes 100–103; test scenes 200–203. No game captures, photographs or downloaded model weights were used in training.

| Held-out scene | Bicubic PSNR | Neural PSNR |
| --- | --- | --- |
| 200 | 24.860 dB | 25.263 dB |
| 201 | 25.479 dB | 26.216 dB |
| 202 | 25.574 dB | 25.857 dB |
| 203 | 24.287 dB | 24.728 dB |

The comparison uses bicubic 0.5× downsampling followed by bicubic upsampling on procedural 256 × 256 scenes. PSNR is calculated in display-referred normalized RGB before output quantization. The test distribution is narrow and contains no temporal sequences. It is not a comparison against FSR, native game rendering or a photorealistic reference.

[Evaluation record](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/evaluation-v0.json) · [Model card](https://github.com/ethan03805/enfusion-neural/blob/main/models/MODEL_CARD.md)

## Enfusion capture

Enfusion Lab 0.1.0 discovered stable game build 24903726 and Workbench build 24870687 from local Steam manifests. This is not a remote update check. The isolated addon validated with natural exit 0.

Arland capture used position [2048,60,2048], direction [1,0,0] and a five-second settle. The 1839 × 947 PNG was visually inspected: terrain, trees and sky filled the frame. Capture outer status succeeded; the tool then terminated its owned Workbench process. Raw logs and game imagery remain local.

[Portable capture summary](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/enfusion-capture.json)

## Still unverified

Live integration, linear/HDR scene color, depth, motion vectors, material buffers, pre-HUD presentation, semantic fidelity, temporal stability, total frame times and live memory budget. No cloud GPU has been rented. No claim of broad Enfusion or multi-vendor support is made.
