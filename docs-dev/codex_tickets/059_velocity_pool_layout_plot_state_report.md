# 059 Velocity Pool Layout Plot State Report

## Files changed

- `src/cloudscope/pages/home_page.py`
- `src/cloudscope/views/velocity_pool_view.py`
- `tests/cloudscope/test_velocity_pool_view.py`
- `docs-dev/codex_tickets/059_velocity_pool_layout_plot_state_report.md`

## Summary of implementation

- Added `flex-nowrap` to the scrollable Home page expansion column so the reference image and velocity pool `SmartExpansion` widgets remain vertically stacked instead of wrapping into side-by-side columns.
- Configured the CloudScope velocity pool view with a default `NicePool` `PlotState` using:
  - unfiltered `accept`, `channel`, and `roi_id` pre-filter selections,
  - `parent` as the x/group/color column,
  - `velocity_velocity_mean` as the y column,
  - `PlotType.SWARM` as the initial plot type.
- Replaced the minimal empty fallback DataFrame with a full schema derived from `VelocityAnalysisPool`, ensuring `NicePool` can auto-detect all conventional pre-filter columns before data is loaded.

## Tests added or modified

- Added `test_empty_velocity_pool_dataframe_uses_full_backend_schema`.
- Added `test_velocity_pool_view_configures_default_plot_state`.
- Kept existing row-selection intent test coverage.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_velocity_pool_view.py
```

## Test results

- `3 passed in 1.26s`

## Concerns or follow-ups

- The current velocity pool widget still uses an internal `h-screen` wrapper from `nicewidgets.nicepool`; this is no longer the cause of the side-by-side expansion bug, but it does make the expanded widget tall. A future resizable splitter-pane layout should revisit this alongside any `nicepool` height/fill changes.
- The layout fix was confirmed in the browser before implementation by setting the affected parent column to `flex-wrap: nowrap`; after the change the velocity pool stacked below the reference image and the parent scrolled vertically.
