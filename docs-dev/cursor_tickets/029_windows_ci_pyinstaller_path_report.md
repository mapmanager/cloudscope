# 029 — Windows CI: put venv Scripts on PATH for nicegui-pack

## Problem

Build Windows failed at `nicegui-pack` with:

```text
FileNotFoundError: [WinError 2] The system cannot find the file specified
PyInstaller command:
  pyinstaller --name CloudScope ...
```

CI invoked `.\.venv\Scripts\nicegui-pack.exe` directly. That tool spawns bare
`pyinstaller`. Unlike macOS `build_app.sh` (which activates the packaging venv),
Windows CI did not put `.venv\Scripts` on `PATH`, so CreateProcess could not
find `pyinstaller` even when the package was installed in the venv.

## Goals

1. Prepend `.venv\Scripts` to `PATH` before `nicegui-pack`.
2. Fail fast with a clear error if `pyinstaller` is still not resolvable.

## Files changed

- `.github/workflows/build-windows.yml` — PATH prepend + `Get-Command pyinstaller`
  check before pack
- `docs-dev/cursor_tickets/029_windows_ci_pyinstaller_path_report.md` — this report

## Summary of implementation

The Build Windows app step now mirrors macOS venv activation for tool lookup:
Scripts on `PATH`, then the same `nicegui-pack` arguments as before.

## Tests added or modified

None (CI workflow only).

## Exact test commands run

None locally (Windows runner required).

## Test results

N/A. Recommend `workflow_dispatch` on **Build Windows** after merge.

## Concerns or follow-ups

- Oracle/web NiceGUI `unknown` lockfile fallback remains a separate ticket.
