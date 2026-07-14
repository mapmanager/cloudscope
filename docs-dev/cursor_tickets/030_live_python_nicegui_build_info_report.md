# 030 — Live Python/NiceGUI in App Info (Docker host stamp fix)

## Problem

`./packaging/deploy_cloudscope_web.sh` stamps `_build_info.py` on the host
before `docker compose` build. App Info then showed the host Python (e.g.
Oracle `3.10.12`) and NiceGUI `unknown`, not the container’s Python 3.12 /
installed NiceGUI.

## Goals

1. Keep stamped **build identity** (git, version, timestamps, PyInstaller,
   platform stamp).
2. Always report **live** Python and NiceGUI from the running process.

## Files changed

- `src/cloudscope/build_info.py` — `get_build_info()` always uses
  `sys.version` and installed NiceGUI metadata for those fields
- `tests/cloudscope/test_build_info.py` — assert stamped host Python/NiceGUI
  are ignored
- `docs-dev/cursor_tickets/030_live_python_nicegui_build_info_report.md` —
  this report

## Summary of implementation

Stamped `python_version` / `nicegui_version` are no longer preferred. Docker /
Oracle web deploys show the image stack after rebuild is unnecessary for these
two fields — redeploy or restart is enough once this code is in the image.

## Tests added or modified

- `test_get_build_info_uses_live_python_and_nicegui`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_build_info.py -q
```

## Test results

- `uv run pytest tests/cloudscope/test_build_info.py -q`: **3 passed**

## Concerns or follow-ups

- Platform still prefers the stamp (host platform string). Change later if App
  Info should show container `platform.platform()` instead.
- Redeploy Oracle with this commit so the container picks up the runtime change.
