# 023 — Locked packaging builds (macOS + Windows)

## Problem

Local `./packaging/macos/build_app.sh` used `uv pip install -e .` into a reusable
`.venv-build`. That satisfied loose constraints such as `nicegui>=3.10.0` without
upgrading a stale NiceGUI already present in the venv. A packaged macOS app built
against NiceGUI **3.11.1** silently lost pywebview `confirm_close` (no quit dialog)
because frozen spawn does not re-run the `__mp_main__` `window_args` hook, and
older NiceGUI does not forward picklable `window_args` from the parent.

`./scripts/run app` / `uv.lock` used NiceGUI **3.14.0**, where the dialog works.

Windows CI used `uv sync --frozen` plus an unlocked `uv pip install pyinstaller`,
which can also drift from the committed lock.

## Goals

1. Make local macOS packaging and GitHub macOS release builds share one locked
   packing path via `packaging/macos/build_app.sh`.
2. Align Windows CI to the same locked packaging pattern.
3. Separate packaging deps (`build` group) from test/lint (`dev` group).
4. Raise the NiceGUI floor to `>=3.14.0` (known-good for frozen native quit).

## Decision (kept)

**CI continues to call `./packaging/macos/build_app.sh` for app creation.**

Codesign / notary / staple remain subsequent workflow steps. One pack script
keeps local smoke tests equal to what CI packages.

## Files changed

- `pyproject.toml` — `nicegui>=3.14.0`; new `[dependency-groups].build` with
  `pyinstaller`; remove `pyinstaller` from `dev`
- `uv.lock` — regenerated for the above
- `packaging/macos/build_app.sh` — `UV_PROJECT_ENVIRONMENT=... uv sync --locked
  --no-dev --group build`; log nicegui / pywebview / pyinstaller versions
- `.github/workflows/build-macos.yml` — comment clarifying pack vs notarization
  ownership (still calls `build_app.sh`)
- `.github/workflows/build-windows.yml` — `windows-2022`; `uv sync --locked
  --no-dev --group build`; version log; drop ad hoc `uv pip install pyinstaller`

## Summary of implementation

Packaging environments now install from the committed `uv.lock` with
`--locked` (fail if `pyproject.toml` and lock disagree). Runtime deps plus the
`build` group (PyInstaller) are installed; docs/dev tools are excluded from
packaging envs.

## Tests added or modified

None (packaging / CI / dependency metadata only).

## Exact test commands run

```bash
uv lock
uv sync --locked --no-dev --group build --dry-run
UV_PROJECT_ENVIRONMENT=packaging/macos/.venv-build uv sync --locked --no-dev --group build
python -c 'import importlib.metadata as m; print(m.version("nicegui"), m.version("pywebview"), m.version("pyinstaller"))'
```

## Test results

- `uv lock` succeeded.
- Locked `--no-dev --group build` sync into `packaging/macos/.venv-build`
  reported **nicegui 3.14.0**, plus pywebview and pyinstaller present;
  `nicegui-pack` on PATH.
- Full `./packaging/macos/build_app.sh` + Finder smoke / Cmd+Q dialog: not
  re-run in this ticket (user already verified quit dialog after deleting
  `.venv-build` and rebuilding against 3.14.0). Recommend one local rebuild
  after pull to confirm the new sync path.

## Concerns or follow-ups

- Local full rebuild still recommended once after this lands:
  `./packaging/macos/build_app.sh` then Cmd+Q quit dialog check.
- Optional workflow_dispatch smoke of `build-macos.yml` /
  `build-windows.yml` without a release tag.
- Dev workflows that previously relied on `dev` including PyInstaller should
  use `--group build` (or `uv sync --group build --group dev`) when packaging
  tools are needed in the default `.venv`.
- **Follow-up (done in 024):** Windows CI must not use bare `uv run` after the
  packaging sync — see `024_windows_ci_no_uv_run_resync_report.md`.
