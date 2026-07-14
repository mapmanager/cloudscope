# 027 — Windows CI build-info schema (App Info parity with macOS)

## Problem

Windows packaging already wrote `src/cloudscope/_build_info.py` before
`nicegui-pack`, but the module used top-level names (`APP_NAME`, `VERSION`,
…) that `cloudscope.build_info.get_build_info()` never reads.

Runtime App Info only imports `BUILD_INFO` from `cloudscope._build_info` (same
contract as `packaging/macos/build_info.sh`). Packaged Windows builds therefore
fell back to development/`unknown` values.

Docker/compose identity stamping is deferred to a later ticket.

## Goals

1. Emit the macOS-compatible `BUILD_INFO` dict from Windows CI before pack.
2. Use full git history on checkout (`fetch-depth: 0`) for tag/commit identity.
3. Remove the transient `_build_info.py` after pack (macOS EXIT-trap equivalent).

## Files changed

- `.github/workflows/build-windows.yml` — checkout depth; rewrite Write build
  metadata to emit `BUILD_INFO`; cleanup step after pack
- `docs-dev/cursor_tickets/027_windows_build_info_schema_report.md` — this report

## Summary of implementation

- Checkout now uses `fetch-depth: 0` (aligned with `build-macos.yml`).
- “Write build metadata” runs `.venv` Python to gather git / package / platform
  fields and write `BUILD_INFO = {...}` with the same keys as
  `packaging/macos/build_info.sh`.
- Version comes from the existing `Resolve project version` step via
  `BUILD_APP_VERSION`.
- “Remove transient build metadata” runs with `if: always()` after
  `nicegui-pack` so the frozen app keeps the stamp while the workspace file is
  deleted (file remains gitignored).

## Tests added or modified

None (workflow-only change; existing `tests/cloudscope/test_build_info.py`
covers runtime fallback API).

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_build_info.py -q
```

Plus a local smoke of the `BUILD_INFO` writer logic (dict keys + `exec`able
module text) matching the workflow Python payload.

## Test results

- `tests/cloudscope/test_build_info.py`: **2 passed**
- Local `BUILD_INFO` writer smoke: **OK** (keys match macOS schema)

Full Windows `nicegui-pack` path: not run in this ticket (requires
`windows-2022` / `workflow_dispatch`). Recommend a dispatch build and App Info
check on the resulting exe.

## Concerns or follow-ups

- Docker / `docker-compose.yml` build identity: deferred (env overlay and/or
  Dockerfile build-args + shared writer).
- Optional later DRY: extract a shared `write_build_info.py` used by macOS
  script and Windows CI.
