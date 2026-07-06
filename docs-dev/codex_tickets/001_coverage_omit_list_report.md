# Ticket 001 — Coverage omit list

## Files changed

- `pyproject.toml` — added `[tool.coverage.run] omit = [...]`
- `docs/codex_tickets/001_coverage_omit_list_report.md` (this report)

## Summary of implementation

Added a coverage omit list under `[tool.coverage.run]` to exclude code that
cannot be meaningfully unit-tested without a real browser, native window, or
`ui.run` invocation, and that is not shipped production logic:

```toml
[tool.coverage.run]
omit = [
    "src/cloudscope/app.py",
    "src/cloudscope/devtools/*",
    "src/nicewidgets/raster_viewer/demo/*",
    "src/nicewidgets/table_widget/demo_app.py",
    "src/nicewidgets/gui_defaults.py",
]
```

Rationale:

- `src/cloudscope/app.py` — NiceGUI `ui.run` entry point.
- `src/cloudscope/devtools/*` — diagnostics/telemetry helpers not part of the
  shipped product workflow.
- `src/nicewidgets/raster_viewer/demo/*` and
  `src/nicewidgets/table_widget/demo_app.py` — demo apps.
- `src/nicewidgets/gui_defaults.py` — NiceGUI style constants only.

Real product code that is currently hard to test (e.g. `_py_web_view.py`,
`utils/logging.py` modules) was **not** omitted; it remains visible to coverage
so future tickets can address it.

## Tests added or modified

None. This ticket only changes coverage configuration.

## Exact test commands run

```bash
uv run pytest --cov=src --cov-report=term -q
```

## Test results

- 429 passed
- Coverage: **61% → 63%** (no test changes; pure config effect)
- Total statements went from 9778 to 9334 (-444 omitted statements)
- Missed lines went from 3833 to 3448

## Concerns or follow-ups

- `src/cloudscope/_py_web_view.py` (9%, 89 statements) is still counted. Its
  `_prompt_for_path` function has a testable `webview is None` branch worth
  adding in a future ticket.
- `src/cloudscope/utils/logging.py`, `src/nicewidgets/utils/logging.py`,
  `src/acqstore/utils/logging.py` are all ~35% and could be tested at the
  level-config boundary in a future ticket.
- CI workflow `.github/workflows/tests.yml` already uses `--cov=src/cloudscope
  --cov=src/acqstore --cov=src/nicewidgets`. The new `omit` is honored
  automatically by `pytest-cov` via `[tool.coverage.run]`.
