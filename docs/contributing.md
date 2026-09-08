# Contributing

Read the shared [engineering protocol](https://github.com/ethan03805/enfusion-neural/blob/main/AGENTS.md), [handoff](status.md) and [roadmap](roadmap.md). The same instructions apply to human engineers, Codex and Claude Code. Start from a bounded next task with an acceptance criterion.

## Change workflow

Use a branch after the initial bootstrap. Keep model, backend, data and adapter changes separate where review benefits. Add a decision record when changing a major assumption. Update status and evidence after a milestone, including failures and limitations. Never claim a test passed because a tool launched successfully.

```powershell
python -m unittest discover -s tests -v
cmake --build build --config Release
python -m enr.cli benchmark --model models/bootstrap-v0.json --width 127 --height 65 --out runs/check
```

Run GPU workloads one at a time. A Windows CI GPU smoke test may skip if the hosted runner has no hardware adapter; that is not hardware validation. Hardware execution is established by the separately recorded benchmark runs.

Smoke tests check one dispatch at each size and retain inputs, logs and manifests in a new `runs/smoke-*` directory. They do not benchmark throughput. CI uploads these files when a check fails. For performance, use the benchmark command with its full warmup/sample counts.

## Documentation site

```powershell
python -m pip install -r requirements-docs.txt
python scripts/build_docs.py
python -m http.server 8000 --directory dist
```

Install into an activated virtual environment. Open `http://localhost:8000`. Edit Markdown in `docs/`, shared CSS in `site/style.css` and page order in the build script. The build checks internal file links and emits relative links so the same output works under a GitHub Pages project path. The theme preference uses a small script and local storage; reading and navigation work without JavaScript. With no saved selection, the colors follow the system preference.

Run `node scripts/check_theme.cjs` after changes to theme behavior. Keep promotional copy and personal machine specifications out of the rendered documentation. Hardware identities remain in raw measurement records for provenance.

The `Pages` GitHub Actions workflow builds and deploys on pushes to main after the test job passes. Use repository Settings → Pages → GitHub Actions. The `CI` workflow also builds Windows native code and verifies Python behavior on Linux. No game installation or game asset is required in CI.

## Handoff record

Leave the exact commit, commands run, output/evidence locations, unresolved concerns and the next acceptance criterion. Avoid putting local user profiles, access tokens or raw game logs into public documentation. The code license covers original code, fixtures and model weights only.
