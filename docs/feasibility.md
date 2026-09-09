# Selective neural rendering feasibility

Reviewed 8 September 2026 against the installed public SDK and existing capture evidence. Recorded builds: game 24903726, Tools 24870687. This review used read-only inspection and primary sources; it launched no engine or GPU experiment and collected no game assets or photographs.

Subsequent work is tracked in [scene diversity](lighting-diversity.md): bounded resource/location inventories have now run in isolated Workbench addons. They do not establish an all-asset inventory or a live neural bridge. The dated review below describes what was established when it was written.

**The proposal is technically credible as a research architecture, but a live Reforger implementation is not established today.** We can train asset-conditioned models offline and use documented material replacement workflows. We have not verified the renderer access needed to reduce selected shading work, pass the necessary surface information to a network, and return its output at the correct scene stage. Training on every asset would not resolve that interface gap.

## What the installed tools establish

“Documented” below means an API declaration or official workflow exists. It does not mean this project has successfully exercised it.

| Capability | Evidence and practical limit |
| --- | --- |
| Controlled scene images | Locally verified viewport PNG export, camera/environment telemetry and offline GPU processing. These are display-referred images, without a verified presentation fence. See [integration](integration.md) and [capture controls](capture-controls.md). |
| Select asset materials | Official workflows permit assigning materials to prefab/entity MeshObject components. The SDK exposes material parameters and material resource names. This makes a small isolated material-quality experiment plausible; it does not establish arbitrary shader replacement. [Weapon modding](https://community.bistudio.com/wiki/Arma_Reforger%3AWeapon_Modding). |
| Replace resources | The official table marks models and textures as replaceable, while materials can be modified/inherited. Replacement is distinct from extracting editable original meshes or source textures. [Data modding basics](https://community.bistudio.com/wiki/Arma_Reforger%3AData_Modding_Basics). |
| Import original source assets | The documented texture pipeline imports source images into compressed EDDS resources. Original assets can therefore retain source data outside the engine for aligned reference rendering. [Textures](https://community.bistudio.com/wiki/Arma_Reforger%3ATextures). |
| Enumerate resource names | `Workbench.SearchResources` is documented. A resource inventory is possible in principle, but no complete asset/variant inventory was produced by this review. |
| Mesh and texture source access | `MeshObject.Create`, `UpdateVerts` and `UpdateIndices` accept caller-supplied geometry. They are not evidence of extracting all existing meshes. `ExportTextureResourceRequest` has source/destination path fields; the inspected declaration does not establish export formats, coverage or success for shipped resources. |
| Lower internal scene resolution | `RTTextureWidget.SetResolutionScale` explicitly controls the recursive pass driven by that widget. Existing main-viewport scale/FSR probes remain unresolved; the separate widget raw-data request returned false. See the two [viewport reports](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/viewport-probes-v1.json) and [follow-up report](https://github.com/ethan03805/enfusion-neural/blob/main/evidence/viewport-followup-v1.json). |
| Insert neural processing | `BaseWorld.SetCameraPostProcessEffect` accepts an effect type and material path. Neither that declaration nor material parameter APIs prove custom compute dispatch, native texture handles, synchronization, auxiliary buffers or neural output composition. No supported end-to-end bridge has been verified. |

The SDK facts are reproducible in the installed `Workbench/docs/EnfusionScriptAPI/html/` tree: `interfaceMaterial.html` lines 120–140; `interfaceMeshObject.html` lines 126–148; `interfaceWorkbench.html` line 116; `interfaceExportTextureResourceRequest.html` lines 199–200; `interfaceRTTextureWidget.html` lines 367–391; `interfaceImageWidget.html` lines 510–532; and `interfaceBaseWorld.html` line 179. These are HTML source line numbers, not engine implementation source. File hashes and exact local root are in `evidence/feasibility-v1.json`. Public counterparts include [Material](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/interfaceMaterial.html), [RTTextureWidget](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/interfaceRTTextureWidget.html) and [BaseWorld](https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/interfaceBaseWorld.html).

## Where the original detail must live

Drastic quality reduction is safe only for information that can still be recovered from retained inputs or an asset representation. Two different markings can become the same low-resolution pixel pattern. A deterministic RGB-only model then receives identical evidence for two different correct answers. More training cannot remove that ambiguity.

Three distinct approaches deserve separate evaluation:

| Approach | Retained information | Assessment |
| --- | --- | --- |
| Low-quality RGB to enhanced RGB | Image and possibly temporal history | Useful baseline for modest correction. Severe degradation removes markings, thin features and material cues; exact identity cannot be guaranteed. |
| Neural texture/material decoding | Original material information encoded in per-asset latent textures or model weights, addressed by UV and level of detail | Strong candidate for preserving asset identity. Requires integrating the decoder into material sampling, or decoding conventional textures ahead of use. Offline baking is accessible but does not by itself save shading cost. |
| Neural shading reconstruction | Geometry/visibility, depth, normals, material identity/features, view/light state and trustworthy motion/history | Candidate for reducing costly shading while keeping surfaces stable. Buffer access, dynamic lighting coverage and the cost of retained inputs are essential and unresolved in Reforger. |

These are engineering assessments. Published work provides precedent, not a Reforger performance result. *Random-Access Neural Compression of Material Textures* encodes material texture sets and supports on-demand GPU decoding; it preserves information in a compressed representation instead of reconstructing from deliberately destroyed RGB evidence. Its decoder also has a cost. [NVIDIA research paper](https://research.nvidia.com/publication/2023-08_random-access-neural-compression-material-textures).

*Deferred Neural Rendering* learns surface-attached feature maps together with a renderer using geometry proxies. That supports asset-specific neural representations, while leaving generalization to new conditions an experiment. [Thies et al., 2019](https://arxiv.org/abs/1904.12356).

The initial experiment should preserve rasterized geometry, occlusion and silhouettes. Reduce a specified lighting term or material detail separately, rather than reducing geometry and hoping reconstruction restores it. Asset IDs identify the object; UVs locate a point on its surface; normals and material parameters describe its response. IDs alone cannot locate a scratch, decal or clothing pattern. Dynamic deformation, changing textures and attachments require corresponding state. Reflections and indirect illumination also depend on other surfaces, including offscreen ones.

Lower texture resolution does not imply a proportional frame-time improvement. It can reduce storage, bandwidth or streaming pressure while the frame remains limited by geometry, CPU work or lighting. The necessary inequality is: **avoided engine cost exceeds neural processing, retained feature generation, synchronization and composition cost**. Measure the whole application after the bridge exists.

## Training on all assets and real photographs

Training on known assets can improve recognition and provide detailed priors. A practical design is a shared reconstruction model plus versioned per-asset features, with an ordinary rendering fallback for unknown assets. An “all assets” training set is not an exhaustive state set: viewpoints, distance, LOD transitions, exposure, weather, wetness, damage, animation, attachments, terrain blending and mod content create additional combinations. Nearby frames must not leak across evaluation splits. Hold out camera paths, lighting conditions and asset families; separately test unseen mod assets and changed resource versions.

High-quality game renders provide aligned targets for recovering game appearance. They do not become photographic ground truth merely because there are many of them. Real photographs can inform plausible roughness, reflectance and lighting, but a photograph of the same vehicle type may have different markings, geometry, damage and surface age. Unregistered photos are weak appearance evidence, not pixel-aligned targets for the exact game asset.

For identity-preserving reference data, begin with one original object whose geometry/materials are available. Capture calibrated multiple views, camera poses, scale and color references; map observations to the object's surface; model or measure illumination. Preserve authored markings and geometry when fitting material response. Evaluate under lighting and viewpoints excluded from fitting. This is a proposed capture protocol, not a dataset collected here.

The need to separate illumination from material appearance is real: otherwise a shadow in a photograph can become a permanent texture stain, or a highlight can be baked into albedo. NeRFactor demonstrates joint estimation of normals, visibility, albedo and reflectance from posed multi-view images under unknown illumination, and describes the setup as underconstrained. It supports investigating inverse rendering, not treating arbitrary photographs as interchangeable truth. [NeRFactor, 2021](https://xiuming.info/projects/nerfactor/).

Unpaired photo translation is another research route, but its objective must be checked against this project's fidelity contract. Intel's *Enhancing Photorealism Enhancement* uses intermediate rendering representations and studies dataset-layout mismatch; its examples deliberately alter grass appearance and haze. A photographic improvement can therefore conflict with material identity or visibility. [Authors' project](https://isl-org.github.io/PhotorealismEnhancement/).

## Data-use scope

Technical access and permitted use are separate questions. The [Tools EULA](https://store.steampowered.com/eula/1874910_eula_1), under “Your Rights” and “You May Not,” limits use/content to non-commercial purposes, restricts tool use to making non-commercial content for Bohemia games, prohibits reverse engineering, and contains entertainment/recreation-only wording that lists training and educational purposes among exclusions. It does not explain how those purpose clauses apply to neural optimization for a recreational mod. This review establishes neither a blanket ML authorization nor a blanket ML prohibition.

The [game EULA](https://reforger.armaplatform.com/eula) separately permits screenshots/videos subject to its terms; that is not an explicit license for a redistributed training corpus or weights. The [official FAQ](https://reforger.armaplatform.com/news/eula-faq) distinguishes the game, Tools and Workshop terms and confirms that other creators retain rights to their mods. Owning the game is not evidence that every shipped or Workshop asset has the same reuse terms.

An all-asset corpus or distributed derived model needs a documented basis for its intended use under the applicable licenses. Original-scene experiments can proceed independently. Record each asset/photo source, license, author, permitted transformations and distribution scope. Use original or appropriately licensed photographs; finding an image online does not establish its reuse terms.

## Concrete next gate

The first [synthetic lighting study](lighting-study.md) now implements the source-only feature and RGB/affine comparisons on the original room. It is a within-scene diagnostic; it does not validate a Reforger adapter or new-asset generalization.

Proceed with one original static prop in an isolated scene. Preserve its source mesh, UVs and materials. Establish repeatable camera/light/color alignment and a pair differing in exactly one documented material or lighting cost. First compare ordinary rendering, a simple non-neural correction, RGB reconstruction and reconstruction conditioned on source surface information. Include unseen lighting, oblique views, close-up markings and disocclusion; retain failures.

In parallel with model research, the integration gate requires an authoritative extension sample or documented interface that can pass scene color and required features through an identity control and a visible inversion control at the intended stage. Verify formats, frame identity, resource lifetime, synchronization and placement relative to HUD/scopes/tone mapping. A built-in color effect can be a useful stage probe but cannot certify arbitrary inference support. Repeat previous failed widget/scale probes only when a new documented mechanism explains why they should behave differently.

Acceptance is a reproducible adapter and an explicit available/missing input table, followed by measured whole-frame savings on the accepted quality setting. Until then, describe results as offline appearance experiments. Scaling training to the whole game is premature while either source information or the live bridge is missing.
