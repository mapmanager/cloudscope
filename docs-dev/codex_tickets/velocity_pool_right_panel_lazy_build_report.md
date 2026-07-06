# Velocity pool right panel — lazy build and production defaults

## Files changed

- `src/nicewidgets/nicepool/plot_pool_controller.py`
- `src/nicewidgets/nicepool/nice_pool.py`
- `src/cloudscope/views/velocity_pool_view.py`
- `src/cloudscope/pages/home_page.py`
- `src/cloudscope/views/header_view.py`
- `src/cloudscope/desktop_launcher.py`
- `packaging/macos/_config.sh`
- `packaging/macos/build_app.sh`
- `.github/workflows/build-macos.yml`
- `.github/workflows/build-windows.yml`
- `docker-compose.yml`
- `Dockerfile`
- `README-DEV.md`
- `tests/nicewidgets/test_nicepool.py`
- `tests/cloudscope/test_velocity_pool_view.py`
- `tests/cloudscope/test_desktop_launcher.py`
- `tests/cloudscope/test_home_page_right_pool_panel.py`
- `tests/cloudscope/test_header_view.py`

## Summary of implementation

- **Lazy build on first open:** Right-panel `VelocityPoolView` is not built at page compose when collapsed. Unified `_sync_right_pool_panel()` handles header toggle, splitter drag, and double-click handle: first open calls `build()` then `show()`; re-open calls `show()` + `relayout_plots()`.
- **`relayout_plots()` API:** Added on `PlotPoolController`, `NicePool`, and `VelocityPoolView` (delegates to `_rebuild_plot_panel()`).
- **Control panel scroll:** Replaced `h-screen` with `h-full min-h-0` in NicePool layout; control panel container uses `h-full min-h-0 overflow-hidden`.
- **Header:** **Open Pool** shown only when Option C launcher is active; **Velocity Pool** button toggles right panel when `SHOW_VELOCITY_POOL_RIGHT_PANEL`.
- **Single-window default:** `CLOUDSCOPE_SINGLE_WINDOW` defaults to `true`; Option C opt-in via `CLOUDSCOPE_SINGLE_WINDOW=0`, `CLOUDSCOPE_MULTI_WINDOW=1`, or `CLOUDSCOPE_DESKTOP_LAUNCHER=option_c`. Env baked into macOS/Windows packaging and CI workflows; documented in Docker files.
- **Circular import:** `get_pool_launcher` imported lazily inside `HomePage.build()` to avoid `home_page` ↔ `desktop_launcher` cycle.

## Tests added or modified

- Added: `test_nicepool_relayout_plots_rebuilds_plot_panel`
- Added: `test_velocity_pool_view_relayout_plots_delegates_to_nicepool`
- Modified: `tests/cloudscope/test_desktop_launcher.py` (single-window default)
- Modified: `tests/cloudscope/test_home_page_right_pool_panel.py` (flag on)
- Modified: `tests/cloudscope/test_header_view.py` (`on_velocity_pool_toggle` param)

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_nicepool.py tests/cloudscope/test_velocity_pool_view.py tests/cloudscope/test_desktop_launcher.py tests/cloudscope/test_home_page_right_pool_panel.py tests/cloudscope/test_header_view.py
uv run pytest
```

## Test results

- Focused: 54 passed
- Full suite: 1276 passed

## Concerns or follow-ups

- **Reset layout:** `_reset_home_layout` collapses the right pool splitter but does not yet call `_sync_right_pool_panel()` to hide the lazy-built view — follow-up ticket.
- **Save-on-quit on single-window:** Option C custom save dialog not ported to single-window path — future ticket.
- Manual UX: verify Plotly points render on first drag-open and control panel scroll reaches bottom controls.
