# Ticket 071: Pool plot theme wiring and slim pool header (cloudscope)

## Files changed

### Modified
- `src/cloudscope/views/velocity_pool_view.py`
- `src/cloudscope/pages/pool_page.py`
- `src/cloudscope/pages/home_page.py`
- `src/cloudscope/views/header_view.py`
- `tests/cloudscope/test_pool_page.py`

### Created
- `docs-dev/codex_tickets/071_pool_plot_theme_cloudscope_report.md`

## Summary

Wired pool plots to application theme the same way as `PrimaryImageView`:

- `VelocityPoolView` accepts `dark_mode` and optional `dark_mode_provider`
- Subscribes to `ThemeChanged` and calls `NicePool.set_dark_mode()`
- `pool_page` passes initial `dark_mode` from `runtime.app_config`

Slimmed the standalone pool window header to title only:

- Removed Open Main, theme toggle, and GitHub from `/pool`
- Added `show_github: bool = True` to `build_main_header()` (home page unchanged)
- Added `enable_page_dark_mode()` so the pool page creates `ui.dark_mode` and
  subscribes to `ThemeChanged` (NiceGUI Quasar chrome, not just Plotly layout)

Pool plots follow theme toggles on the main window via shared `event_bus` / `app_config`.

## Tests added or modified

- `tests/cloudscope/test_velocity_pool_view.py` — dark_mode init, ThemeChanged, provider sync
- `tests/cloudscope/test_pool_page.py` — page dark mode wiring and disconnect cleanup
- `tests/cloudscope/test_header_view.py` — `enable_page_dark_mode()` sync

## Test commands run

```bash
uv run pytest tests/cloudscope/test_velocity_pool_view.py tests/cloudscope/test_pool_page.py tests/cloudscope/test_theme_event.py
uv run pytest
```

## Test results

```
35 passed (focused)
1173 passed, 2 skipped, 13 warnings (full suite)
```

## Concerns or follow-ups

- Pool window has no local theme toggle; users change theme on the main window only.
