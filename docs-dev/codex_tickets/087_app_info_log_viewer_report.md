# 087 App Info log viewer

## Files changed

- `src/cloudscope/utils/logging.py` — added `read_log_tail()`
- `src/cloudscope/utils/file_manager.py` — added `open_path_with_default_app()`
- `src/cloudscope/views/app_info_view.py` — Open Logs button + SmartExpansion log preview
- `tests/cloudscope/test_logging.py` — new
- `tests/cloudscope/test_file_manager.py` — open-path tests
- `tests/cloudscope/test_app_info_view.py` — new
- `docs-dev/codex_tickets/087_app_info_log_viewer_report.md` — this report

## Summary

Expanded the App Info tab with:

1. **Open Logs** — opens `cloudscope.log` in the OS default application. Disabled when `CLOUDSCOPE_REMOTE` is truthy (remote/server deployments). Enabled for local native runs, local server-mode runs, and packaged desktop builds.
2. **Recent logs** — `SmartExpansion` containing a readonly `ui.textarea` (monospace, 20 rows) that loads the last 200 lines from `cloudscope.log` when expanded. Placeholder text is shown when file logging is disabled or the log file is missing.

Backend helpers:

- `read_log_tail(*, max_lines=200, log_path=None)` — efficient tail read; no module-level line-count constant (callers pass `max_lines`).
- `open_path_with_default_app()` — macOS `open`, Windows `os.startfile`, Linux `xdg-open`.

**Logging scope note:** CloudScope, NiceWidgets, and AcqStore each configure separate loggers with `propagate=False` and separate files (`cloudscope.log`, `nicewidgets.log`, `acqstore.log`) under their respective `platformdirs` config directories. The App Info viewer shows **CloudScope logs only**.

## Tests added or modified

- `tests/cloudscope/test_logging.py`
- `tests/cloudscope/test_file_manager.py`
- `tests/cloudscope/test_app_info_view.py`

## Test commands run

```bash
uv run pytest tests/cloudscope/test_logging.py tests/cloudscope/test_file_manager.py tests/cloudscope/test_app_info_view.py
```

## Test results

21 passed (1.61s):

- `tests/cloudscope/test_logging.py` — 6 passed
- `tests/cloudscope/test_file_manager.py` — 8 passed
- `tests/cloudscope/test_app_info_view.py` — 7 passed

## Concerns or follow-ups

- Unified cross-package log view would require a separate ticket (merge tails or reconfigure logging hierarchy).
- Browser readonly textarea copy/select was not manually verified in this pass; NiceGUI 3.10 `ui.textarea` supports standard Quasar `readonly` via `.props('readonly')`.
