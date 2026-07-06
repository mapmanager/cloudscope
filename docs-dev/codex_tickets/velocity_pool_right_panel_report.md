# Velocity pool right splitter panel

## Files changed

- `src/cloudscope/app_config.py`
- `src/cloudscope/views/splitter_manager.py`
- `src/cloudscope/pages/home_page.py`
- `src/cloudscope/views/header_view.py`
- `tests/cloudscope/test_app_config_splitters.py`
- `tests/cloudscope/test_splitter_manager.py`
- `tests/cloudscope/test_home_page_right_pool_panel.py`
- `tests/cloudscope/test_header_view.py`
- Deleted: `tests/cloudscope/test_home_page_pool_drawer.py`

## Summary of implementation

- Removed failed `ui.right_drawer` spike (`SHOW_VELOCITY_POOL_RIGHT_DRAWER`, header **Pool Drawer** button).
- Added `SHOW_VELOCITY_POOL_RIGHT_PANEL = False` (default off) for a bare resizable right splitter panel.
- When enabled, wraps the main workspace in `SplitterId.RIGHT_POOL`: `before` = existing workspace, `after` = `VelocityPoolView` only (no icon bar).
- Collapsed startup: main ~98%, pool ~2%; remembered open width default 72% main / 28% pool (`home_right_pool_open_splitter_pct`).
- User resize via splitter drag; double-click handle toggles open/collapsed.
- Pool view `show()` / `hide()` synced from splitter collapsed state.
- Option C **Open Pool** unchanged.

## Tests added or modified

- Added: `tests/cloudscope/test_home_page_right_pool_panel.py`
- Added: `test_splitter_manager_right_pool_open_closed`
- Modified: `tests/cloudscope/test_app_config_splitters.py`, `tests/cloudscope/test_header_view.py`
- Deleted: `tests/cloudscope/test_home_page_pool_drawer.py`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_home_page_right_pool_panel.py tests/cloudscope/test_splitter_manager.py tests/cloudscope/test_app_config_splitters.py tests/cloudscope/test_header_view.py
uv run pytest
```

## Test results

- Focused: 36 passed
- Full suite: 1273 passed

## Concerns or follow-ups

- Manual UX: set `SHOW_VELOCITY_POOL_RIGHT_PANEL = True` and verify Plotly resize while dragging.
- Reset-home-layout does not yet collapse the right pool panel.
