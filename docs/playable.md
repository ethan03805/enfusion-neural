# Playable prototype

Updated 10 September 2026. **The live pipeline works; the requested photorealistic appearance is unfinished.** An isolated addon starts local single-player Reforger, and a Windows companion runs a pretrained exposure network over its actual 2560 × 1440 RGB frames on the RX 7800 XT.

## Run the build

[Download the Windows research build](downloads/playable-pipeline-2026-09-10.zip). Extract the entire folder, close any existing Reforger session and double-click **Start-Playable.cmd**. This PC needs its Steam game installation and Python 3 launcher. No PyTorch, CUDA or pip installation is needed to play.

- **F8:** expose the original game / resume the overlay.
- **F9:** switch identity / neural enhancement inside the companion.
- **F10:** quit the companion; the original game stays open.

The default starts free play in the town with standard settings. Optional: `Start-Playable.cmd --preset combined --scene town-evening --strength 0.35`. Scene choices are town, town-evening and foliage. Free play has no automatic movement. Use `--viewer` for a separate ordinary window.

Each launch writes an isolated addon, copied settings and logs into a new `runs/play-...` folder. The Steam installation and original profile are unchanged. The package includes source, hashes and separate model attribution. [Build from source](getting-started.md).

**Input limit:** engine actions verify a walking soldier and camera turn while enhancement is visible. Physical WASD/mouse routing through the overlay still awaits a user check. The UI automation driver refuses mouse actions through the covering companion. Use F8 or F10 if controls fail.

## Normal-speed gameplay

Three independent town runs follow the same declared path: 20 seconds walking, then a 10-second heading sweep. Each complete recording lasts 34 seconds, including lead-in and tail. There is no speed change, optical flow or generated motion. Each native 1440p input is scaled to a 1280 × 720 panel for the web comparison; audio was not captured.

<figure class="motion-comparison">
<video controls playsinline preload="none" poster="media/playable-town-poster.png" width="3840" height="760" aria-label="Normal-speed town gameplay, standard, reduced and reduced plus neural"><source src="media/playable-town-unretimed.mp4" type="video/mp4"><a href="media/playable-town-unretimed.mp4">Download town gameplay</a></video>
<figcaption>Town · standard / reduced / reduced + neural · 34 seconds at 1× speed</figcaption>
</figure>

<figure class="motion-comparison">
<video controls playsinline preload="none" poster="media/playable-foliage-poster.png" width="3840" height="760" aria-label="Normal-speed foliage gameplay, standard, reduced and reduced plus neural"><source src="media/playable-foliage-unretimed.mp4" type="video/mp4"><a href="media/playable-foliage-unretimed.mp4">Download foliage gameplay</a></video>
<figcaption>Foliage/fence collision check · standard / reduced / reduced + neural · 34 seconds at 1× speed</figcaption>
</figure>

The foliage attempt reaches a solid fence and stops, retaining the cover collision. The reduced-only run also takes a different line around the tree, with a maximum sampled camera deviation of 1.87 metres. This is retained as a visibility/collision check; it is **not an accepted matched moving-foliage benchmark**. Much of its timing window is stationary.

Capture starts near simulation second 28 in each run. Initialization and head movement differ, so these are repeat paths, not pixel-aligned images. The town recordings' sampled camera positions differ by at most 0.21 metres at the same simulation times. The compositor holds the last available frame of a slower input, preserving elapsed time. Native VFR clips and timestamps remain local.

## Application performance

The table uses a 30-second town path **without recording**. Output is 2560 × 1440. Every varied setting is checked through engine readback. Geometry, texture and vegetation settings retain the user's saved values. Standard uses native scale, FSR off and high local/distant shadows.

| Configuration | Game presents/s | Game interval p50 / p95 / p99, ms | Intervals >33.3 ms |
| --- | ---: | ---: | ---: |
| Standard | 87.96 | 11.35 / 13.43 / 14.45 | 0 |
| 75% scale + FSR1 | 97.15 | 10.12 / 13.04 / 15.68 | 3 |
| Medium local / low distant shadows | 88.18 | 11.32 / 13.51 / 14.59 | 0 |
| SSDO + SSR disabled | 97.55 | 10.19 / 12.44 / 13.45 | 0 |
| All three reductions | 104.75 | 9.37 / 12.16 / 14.62 | 2 |
| Reduced + neural | 88.13 | 11.29 / 15.97 / 18.31 | 0 |
| Standard + neural | 72.05 | 13.80 / 18.11 / 20.37 | 0 |

The combined reduction creates 19.1% more game presentation throughput in this town sample. Shadow reductions alone make little difference. Adding enhancement to the combined reduction brings game throughput close to standard; adding it to standard costs substantially more.

**Companion output, reduced + neural:** 60.69 presents/s; 15.55 / 30.43 / 32.05 ms p50 / p95 / p99 intervals. Twelve intervals exceed 33.3 ms; maximum 41.46 ms. Twenty queued source frames are discarded in favor of newer frames. GPU copy + inference + draw take 3.44 ms median, 6.11 ms p95 and 7.64 ms p99. This is not a locked-60 result.

These are application Present calls, including frames that may never be displayed. PresentMon CPU traces exclude null-swapchain WGC events that otherwise falsely double the companion count. Game and companion run concurrently; GPU dispatch time is not substituted for whole-application FPS. One pass per setting provides no confidence interval or general performance guarantee. Sampled town camera paths differ by at most 0.17 metres.

**Recording overhead:** the town clips measure 77.68 / 97.35 / 81.47 game presents/s for standard / reduced / reduced + neural. The companion produces 60.43 presents/s, while the recording retains 1,845 frames over 34 seconds (54.26 frames/s). WGC recording performs an explicit CPU readback and NV12 conversion before AMD hardware encoding. The normal companion path has no full-frame CPU readback.

[Complete measurement record](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/playable-comparison-v1.json) contains frame quantiles, path telemetry, configuration readback and raw-artifact hashes.

Additional recorded checks, with the foliage limitations above:

| Recorded case | Game presents/s | Game p95 / p99, ms | Companion presents/s | Companion p95 / p99, ms |
| --- | ---: | ---: | ---: | ---: |
| Foliage/fence standard | 66.95 | 17.89 / 19.70 | — | — |
| Foliage/fence reduced | 81.14 | 15.76 / 17.06 | — | — |
| Foliage/fence reduced + neural | 69.91 | 18.99 / 22.09 | 60.10 | 30.55 / 32.54 |
| Evening town reduced + neural | 82.03 | 17.42 / 20.29 | 60.65 | 30.38 / 32.15 |

The evening check is a single enhancement run, with no evening baseline claim. The rebuilt package changes C++ runtime linkage and metadata only; its unchanged shader still passes CPU parity.

### Ten-minute runtime check

A separate 600-second reduced + neural run completes without a crash, recorded hide or presentation timeout. It follows the existing 30–60 second walk/turn segment and then holds a stationary town camera. This checks sustained processing, not ten minutes of movement. No video was recorded; ordinary Codex/documentation work continued on the CPU.

| Application | Presents/s | Interval p95 / p99, ms | Maximum interval, ms | Intervals >33.3 / >50 ms |
| --- | ---: | ---: | ---: | ---: |
| Game | 89.28 | 15.56 / 18.19 | 39.72 | 3 / 0 |
| Companion | 61.09 | 29.74 / 31.87 | 52.90 | 133 / 1 |

The companion processes 36,654 frames over 600.007 seconds. Each minute contains 60.70–61.45 presents/s; none falls below 30. GPU copy/network/draw take 3.50 ms median and 6.19 ms p95. Capture-to-Present-call age is 6.60 ms median / 13.95 ms p95, with raw negative offsets retained. It discards 380 queued source frames in favor of newer ones. PresentMon and native cadence agree; 37,015 internal capture events are excluded from application throughput. These measurements do not establish displayed-frame cadence, physical latency, manual controls or semantic fidelity.

[Complete ten-minute and per-minute evidence](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/playable-soak-v1.json). Reproduce with `scripts/benchmark_playable.py --out NEW_DIRECTORY --preset combined --mode neural --trace cpu --soak-seconds 600`; summarize with `scripts/summarize_soak.py RUN_DIRECTORY --evidence OUTPUT_JSON`.

## Latency and fallback

An earlier live HWND sample joins **895 displayed frames**: **12.61 ms median, 18.12 ms p95, 20.98 ms p99** from WGC compositor timestamp to PresentMon-reported display. This excludes mouse/keyboard sampling and physical panel response. It is a separate early scene sample using engine defaults.

In the moving town path, capture timestamp to the companion's Present call is **6.75 ms median / 14.20 ms p95**. Raw signed values include negative compositor offsets and remain in the evidence. Moving-path display/GPU traces are unavailable, including a display-only retry. The standard baseline's resolved GPU trace measures 11.22 ms median game GPU activity; missing channels elsewhere are not reported as zero. Full added physical latency remains unmeasured.

F8 exposes the original game. An earlier retained test measured 1.38 ms from handling the hotkey to hiding the overlay, excluding keyboard sampling. Loss of focus, minimization, stale frames or a presentation timeout also exposes source. Invalid curves fall back to source pixels. Fixed HUD margins, near-black/highlight protection and bounded brightness reduce appearance risk; they are not a semantic reconstruction-failure detector.

The packaged launch test processes 3,770 frames, verifies both F9 modes, F8 bypass/resume and clean F10 exit. Its F8 handler-to-hide log measures 1.20 ms. The captured 1440p source/output pair changes at most 15 code values per channel. All 76 CPU tests and native network parity pass. [Package verification](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/playable-package-v1.json).

## Appearance and pretrained selection

The [appearance candidate comparison](model-evaluation.md) now includes REGEN on RX 7800 XT DirectML and DeepLPF on CPU, with raw outputs and rejection evidence. The downloadable build still uses the verified exposure model below.

The available input is **display-referred RGB with HUD**, not depth, normals, motion or material buffers. The model cannot recover a verified scene-lighting representation from those absent inputs.

**Zero-DCE++** is the working native model: 10,561 parameters, 320 × 180 FP32 curve prediction and full-resolution bounded composition. Its output matches the independent author's checkpoint reference to a maximum error of 0.000000075 over 172,800 values. It preserves source pixel coordinates and chroma while limiting brightness change. The change is modest; some ground surfaces become flatter or brighter. No photorealistic material gain is accepted.

<section class="comparison" data-comparison aria-label="Same game frame before and after live neural enhancement">
<div class="comparison-images">
<figure class="comparison-before"><img src="media/playable-source.png" width="2560" height="1440" loading="lazy" alt="Original first-person town frame"><figcaption>Source game</figcaption></figure>
<figure class="comparison-after"><img src="media/playable-neural.png" width="2560" height="1440" loading="lazy" alt="Same frame after bounded native neural exposure enhancement"><figcaption>Live Zero-DCE++ · bounded</figcaption></figure>
<span class="comparison-divider" aria-hidden="true"></span>
</div>
<label class="comparison-control" hidden>Reveal source<input type="range" min="0" max="100" value="50" aria-label="Source image visible"><output>50% original</output></label>
</section>

This is the exact source/output frame pair from the early live loop, before the profile correction. [Source PNG](media/playable-source.png) · [Native output PNG](media/playable-neural.png).

**Image-Adaptive-3DLUT** was evaluated on two actual captured views using its pinned photographic sRGB checkpoint. Raw output clips 6.95% and 4.92% of channel values and visibly crushes foliage shadows. A bounded blend limits the change but supplies no missing material information. It is rejected for live integration. Single-thread CPU classifier samples take 7.42 / 5.46 ms and full-resolution lookup 181.90 / 200.22 ms; these are not GPU or game timings.

<section class="comparison" data-comparison aria-label="Rejected photographic candidate and bounded version">
<div class="comparison-images">
<figure class="comparison-before"><img src="media/playable-photo-raw.png" width="2560" height="1440" loading="lazy" alt="Photographic candidate with clipped foliage shadows"><figcaption>Unrestricted · rejected</figcaption></figure>
<figure class="comparison-after"><img src="media/playable-photo-bounded.png" width="2560" height="1440" loading="lazy" alt="Bounded photographic candidate"><figcaption>Bounded · CPU evaluation</figcaption></figure>
<span class="comparison-divider" aria-hidden="true"></span>
</div>
<label class="comparison-control" hidden>Reveal unrestricted<input type="range" min="0" max="100" value="50" aria-label="Unrestricted image visible"><output>50% original</output></label>
</section>

[Zero-DCE++ author code and weights](https://github.com/Li-Chongyi/Zero-DCE_extension) have separate academic/noncommercial research terms. [Image-Adaptive-3DLUT](https://github.com/HuiZeng/Image-Adaptive-3DLUT) uses Apache-2.0 terms. Pinned revisions and hashes are retained. [HDRNet](https://github.com/google/hdrnet) and [DPIR](https://github.com/cszn/DPIR) were researched but not runtime-evaluated; conversion work is deferred.

[Poly Haven pavement](https://polyhaven.com/a/pavement_04) and [rural asphalt/lighting](https://polyhaven.com/a/rural_asphalt_road) are suitable CC0 appearance references. They are not aligned ground truth for Everon's roads, masonry, roofs or foliage, and have not been used to train this build.

## Boundaries and retained failures

Initial coverage is a town road with buildings, openings, signs and guardrails, a foliage path, an evening town check and a mostly stationary ten-minute runtime test. No game meshes or textures are replaced. The shader performs no spatial reconstruction and has no temporal history; that avoids generated geometry and history ghosting, but does not prove temporal or semantic fidelity. Interiors, scopes, combat visibility, rain, HDR and extended movement remain unaccepted.

The first profile clone was one directory too high; its 114.70 game presents/s result used engine defaults and is not the standard baseline. The corrected launcher writes beneath the nested profile mount and verifies settings. Interrupted early ETW sessions and event-loss runs remain failed. Layered-window presentation variants failed visibly; the normal HWND route is retained. A hard HUD exclusion produced a sky seam and was replaced by a feathered boundary. Direct GPU recording submission failed; the working recorder's CPU conversion is explicit.

These investigations are closed for this iteration. The working code, original outputs and failures remain available. The next acceptance gates are physical input, moving-path display latency, broader visibility/stability checks and a demonstrably better appearance model. [Current status](status.md) · [Roadmap](roadmap.md).

[Microsoft WGC](https://learn.microsoft.com/en-us/windows/apps/develop/media-authoring-processing/screen-capture) · [Win32 capture sample](https://github.com/microsoft/Windows.UI.Composition-Win32-Samples/tree/master/cpp/ScreenCaptureforHWND) · [PresentMon](https://github.com/GameTechDev/PresentMon) · [Reforger startup parameters](https://community.bistudio.com/wiki/Arma_Reforger:Startup_Parameters).
