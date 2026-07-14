# 025 — Packaging CI hardening (lock check, pins, cleanup)

## Problem

After 023/024 locked packaging, a ChatGPT critique asked for residual hardening:
fail fast on lock drift before macOS signing setup; align Python/uv pins with
repo policy; clean transient `_build_info.py` on failed builds; clearer Windows
archive failures. Windows bare-`uv run` risk was already fixed in 024 via direct
`.venv` binaries (kept; not reverted to `uv run --no-sync`).

## Files changed

- `packaging/macos/build_app.sh` — `EXIT` trap for transient build info; log `uv`
  version; remove success-only cleanup block
- `.github/workflows/build-macos.yml` — pin uv `0.9.2`; `python-version-file:
  .python-version`; early `uv lock --check` before secrets/notary
- `.github/workflows/build-windows.yml` — same uv/Python pin + early lock check;
  log uv/Python; verify `dist/CloudScope`; clean `package/` before archive
- `.gitignore` — ignore `src/cloudscope/_build_info.py`
- `docs-dev/cursor_tickets/025_packaging_ci_hardening_report.md` — this report

## Summary of implementation

Hardening only: reproducibility/diagnostics around the existing locked packaging
architecture. No change to notarization flow or macOS `build_app.sh` ownership
by CI.

## Tests added or modified

None.

## Exact test commands run

```bash
uv lock --check
uv --version
```

## Test results

- `uv lock --check` succeeded with local uv **0.9.2** (same pin written into both
  workflows).
- Full `./packaging/macos/build_app.sh` / Windows CI: not re-run in this ticket;
  recommend local rebuild smoke + optional `workflow_dispatch`.

## Concerns or follow-ups

- When upgrading uv, bump the `version:` pin in **both** workflows in the same
  commit as any lockfile changes driven by that uv release.
- Confirm Windows still emits `nicegui-pack.exe` under `.venv\Scripts\` after
  packaging sync.
