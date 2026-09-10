# Engineering protocol

Read README.md, docs/vision.md, docs/architecture.md, docs/status.md and docs/roadmap.md before changing direction. This is the shared contract for Codex, Claude Code and human engineers. CLAUDE.md points here.

- Product priority: faithful photorealism first. Active user target: 2560x1440 at 30–60 FPS on RX 7800 XT in local single-player. The 16.7–33.3 ms budget is the whole application, not the model. Support arbitrary valid image sizes; performance profiles are separate from resolution support.
- The Windows RGB companion captures and processes the live game. Its appearance, input and performance acceptance is tracked in docs/status.md. Do not describe it as a photorealistic model, Workshop release or FSR replacement without evidence. Never equate dispatch time with frame time.
- The v0 CNN is a training/inference reference, not the chosen final appearance model. Preserve the independent CPU reference when changing GPU code.
- Keep engine adapters separate from model/training/backend code. Do not put native hooks or Steam modifications into routine experiments. Resolve the supported bridge before live engine integration.
- Use Enfusion Lab for Workbench discovery, isolated addon validation and capture. Inspect run status, logs and full-size images. Serialize GPU experiments. Preserve failed runs.
- Keep raw capture collections, profiles, machine paths and game assets in ignored runs/ or experiments/local/. The user has authorized selected documentation images and video: publish only reviewed media under docs/media/ with hashes, source records and attribution. Record scaling, encoding and retiming. Keep model outputs labeled and preserve visible failures. Code licensing never grants rights to game content.
- Record real measurements in evidence/. Include input/model hashes, dimensions, adapter, precision, raw timings and scope. Label proposed targets and unknowns. Do not cherry-pick measurements or conceal quality regressions.
- Update docs/status.md after a milestone. Record changed architectural choices in docs/decisions.md. Leave a specific next task with acceptance criteria in docs/roadmap.md.
- Run `python -m unittest discover -s tests -v` for model/contract changes. Build the Windows backend and compare against CPU for GPU changes. Run `python scripts/build_docs.py` for documentation changes. CI validates CPU, Windows GPU smoke and site build.
- A GPU unavailable in CI is explicitly a skip, never evidence of hardware performance. Do not install drivers, rent hardware or launch paid training without user authorization.
- Use branches and reviewable commits after the initial bootstrap. Do not erase other contributors' work or make unrelated cleanup changes. Do not delegate work unless the user asks.
