# 024 — Windows CI: avoid `uv run` re-sync after packaging sync

## Problem

After `uv sync --locked --no-dev --group build`, `build-windows.yml` called
`uv run python` / `uv run nicegui-pack`. Bare `uv run` can re-sync default
dependency groups (including `dev`), undoing the packaging-only environment.
macOS `build_app.sh` already avoids this by activating the sync’d venv and
invoking executables directly.

## Files changed

- `.github/workflows/build-windows.yml` — after locked packaging sync, use
  `.\.venv\Scripts\python.exe` and `.\.venv\Scripts\nicegui-pack.exe` instead of
  `uv run`
- `docs-dev/cursor_tickets/024_windows_ci_no_uv_run_resync_report.md` — this report

## Summary of implementation

Windows release CI now matches the macOS pattern: sync once for packaging, then
run tools from that `.venv` without a second uv sync.

## Tests added or modified

None (CI workflow only).

## Exact test commands run

None (YAML path/command rewrite; not executable on this macOS workspace).

## Test results

N/A locally. Recommend `workflow_dispatch` on **Build Windows** after merge.

## Concerns or follow-ups

- Confirm on a Windows runner that `nicegui-pack.exe` exists under
  `.venv\Scripts\` after the packaging sync (expected via locked `nicegui` +
  `build` / PyInstaller).
