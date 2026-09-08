# Enfusion integration

The installed Workbench can validate isolated addons and export a rendered viewport. That is a useful research interface. It does not expose a verified path for inserting this network into live gameplay.

| Capability | State |
| --- | --- |
| Stable game and Workbench discovery | Verified by Enfusion Lab doctor |
| Isolated addon compilation | Verified in this milestone |
| Explicit camera and full-size scene export | Verified in this milestone |
| Native GPU processing of exported image | Implemented by this repository |
| Pre-HUD linear/HDR scene color | Unverified |
| Native scene-resource handles and fences | Unverified |
| Depth, normals, motion and material textures | Unverified |
| Correct scene-stage output composition | Unverified |
| Packaged runtime mod or multiplayer support | Unverified |

These states describe the inspected interface and local evidence. They are not claims that the engine lacks these buffers internally.

## Bridge experiment

Find an authoritative supported extension interface and a minimal sample. Demonstrate an identity pass at the intended scene stage, then an invert control with exact pixel validation. Record resource formats, color conventions, frame identity, queue ownership, synchronization and output placement relative to HUD, scopes and tone mapping.

If an external Windows capture viewer is used as an intermediate experiment, report capture age, extra latency, copies and missing scene buffers. A post-composited screenshot processor cannot silently inherit guarantees about HUD protection or engine integration.

The same separation applies to other Enfusion games. A shared neural core does not imply access to every game's renderer or asset data. Build and validate each adapter independently.
