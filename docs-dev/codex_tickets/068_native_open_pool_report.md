# Ticket 068: Native Open Pool (Option C default)

## Files changed

### Created
- `src/cloudscope/window_geometry.py`
- `tests/cloudscope/test_window_geometry.py`
- `docs-dev/codex_tickets/068_native_open_pool_report.md`

### Modified
- `src/cloudscope/runtime.py` — `set_process_app_config`, `clear_process_app_config`, `get_process_app_config`; `resolve_runtime_context` reuses process config
- `src/cloudscope/desktop_launcher.py` — Option C default launcher: shared AppConfig, `WindowGeometryTracker`, pool window 1000×800 with offset, main-close destroys pool
- `src/cloudscope/app.py` — `should_use_option_c_desktop()` routing (default local native)
- `src/cloudscope/views/header_view.py` — `_open_pool()` routes to launcher / web / legacy notify
- `src/cloudscope/pages/home_page.py` — guard `app.native.on` when `main_window` absent (Option C)
- `tests/cloudscope/test_desktop_launcher.py` — routing, pool launcher, single-window escape hatch
- `tests/cloudscope/test_runtime.py` — shared process AppConfig tests
- `tests/cloudscope/test_header_view.py` — `_open_pool` routing tests
- `tests/cloudscope/test_app_config.py` — caplog targets `cloudscope.app_config` logger (stable after `app` import in suite)
- `README-DEV.md` — Option C default, `CLOUDSCOPE_SINGLE_WINDOW`, geometry notes

## Summary

Implemented native desktop **Option C** as the default local launch path:

- One process, one NiceGUI server (`native=False`, `show=False`), two manual pywebview windows
- Main window loads `/`; **Open Pool** opens or focuses `/pool` via `PoolLauncher`
- `set_process_app_config()` ensures launcher and `get_current_runtime()` share one `AppConfig` instance
- `WindowGeometryTracker` persists main-window geometry on move, resize, and close
- Pool window: fixed 1000×800, positioned at main window + (40, 40); geometry not persisted
- `CLOUDSCOPE_SINGLE_WINDOW=1` escape hatch restores legacy `ui.run(native=True)`
- Web and remote modes unchanged (`window.open('/pool', 'cloudscope_pool')`)

## Tests added or modified

- `tests/cloudscope/test_window_geometry.py` (new)
- `tests/cloudscope/test_desktop_launcher.py` (expanded)
- `tests/cloudscope/test_runtime.py` (process AppConfig)
- `tests/cloudscope/test_header_view.py` (`_open_pool` routing)

## Test commands run

```bash
uv run pytest
```

## Test results

```
1162 passed, 2 skipped, 13 warnings
```

## Manual tests (operator)

- Default native: `uv run python src/cloudscope/app.py` — main window; Open Pool opens second window; main geometry persists across restart
- Legacy: `CLOUDSCOPE_SINGLE_WINDOW=1 uv run python src/cloudscope/app.py` — single window; Open Pool warns
- Web: `CLOUDSCOPE_NATIVE=false uv run python src/cloudscope/app.py` — Open Pool opens browser tab
- Close main window — pool window closes; config saved

## Concerns / follow-ups

- Pool window geometry persistence remains out of scope
- Manual pywebview verification required on target OS builds
- `CLOUDSCOPE_MULTI_WINDOW` kept as deprecated alias for explicit opt-in tests only
