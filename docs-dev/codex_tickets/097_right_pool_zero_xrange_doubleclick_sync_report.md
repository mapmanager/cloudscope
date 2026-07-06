# 097 — Right pool zero-width close + x-range double-click sync to primary

## Files changed

- `src/cloudscope/app_config.py` — `HOME_RIGHT_POOL_CLOSED_SPLITTER_PCT` 98 → 100
- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py` — `reset_x_axis_to_full_extent()`
- `src/cloudscope/views/primary_image_view.py` — consumer applies auto x-range to viewer
- `tests/cloudscope/test_x_range_view_wiring.py` — updated primary-image consumer tests
- `tests/nicewidgets/test_plotly_viewer_state.py` — test for x-only full-extent reset

## Summary

1. **Right pool toolbar:** Collapsed right-pool splitter now uses **100%** before / **0%** after
   (was 98/2), removing the visible right vertical band. Header “Pool Plots” toggle is unchanged
   (`set_right_pool_open`); collapse detection still uses closed − slack (≥ 98).

2. **X-range double-click sync:** When acq or sum-intensity plots double-click (auto
   `(None, None)`), `PrimaryImageView` now calls `PlotlyRasterViewer.reset_x_axis_to_full_extent()`,
   which relayouts x to the full data extent while preserving the current y zoom. Primary
   double-click still uses the full overview PNG path locally; echo suppression for
   viewer-originated events is unchanged.

## Tests added or modified

- `test_primary_image_view_consumer_auto_range_resets_x_only` (renamed/rewritten)
- `test_primary_image_view_apply_helper_resets_x_when_cache_is_auto` (renamed/rewritten)
- `test_reset_x_axis_to_full_extent_relayouts_x_axis_only` (new)
- `_FakePlotlyViewer` tracks `reset_full_extent_calls`

## Test commands run

```bash
uv run pytest tests/cloudscope/test_splitter_manager.py -q
uv run pytest tests/cloudscope/test_x_range_view_wiring.py -q
uv run pytest tests/nicewidgets/test_plotly_viewer_state.py::test_reset_x_axis_to_full_extent_relayouts_x_axis_only tests/nicewidgets/test_plotly_viewer_x_range.py -q
```

## Test results

All targeted tests passed (38 total across the three commands).

## Concerns or follow-ups

- Browser verification of the 0%-width right pool pane and double-click x-sync in the live
  app was not run in this pass.
- `set_x_axis_range` does not schedule viewport settle; `reset_x_axis_to_full_extent` does.
  If zoomed-in raster tiles look stale after a 1D double-click, confirm in browser and
  tune settle behavior.
