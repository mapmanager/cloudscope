# Ticket 127b — Finish P0: double-click, slider-dead, scrub logging

## Files changed

- `src/nicewidgets/raster_viewer/frontend/plotly_protocol.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
- `src/nicewidgets/raster_viewer/backend/raster_service.py`
- `src/cloudscope/views/primary_image_view.py`
- `tests/cloudscope/test_primary_image_view.py`
- `tests/nicewidgets/test_plotly_viewer_state.py`

## Summary of implementation

### Double-click reset (step 5)

`RASTER_VIEWER_PLOTLY_CONFIG['doubleClick']` was `False`, which suppresses Plotly's
`plotly_doubleclick` event entirely — the custom `_on_plotly_doubleclick` handler
never ran in the browser. Changed to `'reset'` so Plotly emits the event and the
overview-PNG reset path executes after zoom + Z scrub.

### Z slider dead after file switch (step 8)

Two complementary guards:

1. **`on_primary_selection_changed`** now increments `_slice_refresh_generation` so
   in-flight Path B (Z/T scrub) reloads from the previous file are invalidated.
2. **`_refresh_raster_async`** drops stale completions when the snapshot
   `file_id` / `channel` / `z` / `t` no longer match the view's current selection
   (not only when the generation token mismatches).

### DEBUG logging for Z/T scrub (step 4 follow-up)

Added `logger.debug` tracing at:

- `PrimaryImageView._refresh_raster_for_slice_change` / `_refresh_raster_async`
  (Path A vs B, generation, stale drops, pushed `mode`/`level` on Path B)
- `PlotlyRasterViewer.set_data_from_pyramid`, `apply_response` (restyle vs rebuild
  branch), `_refresh_raster_for_viewport`, `set_heatmap_style`, `_refresh_full_png`,
  `_on_plotly_doubleclick`
- `RasterViewService.render`, `full_image_png` (mode, level, shape, bounds)

Enable DEBUG on `cloudscope.views.primary_image_view`,
`nicewidgets.raster_viewer.frontend.plotly_viewer`, and
`nicewidgets.raster_viewer.backend.raster_service` to trace what payload is pushed
on Z scrub (expect Path B → `set_data_from_pyramid` → `full_image_png` /
`image` trace until ticket 128 atomic viewport swap).

## Tests added or modified

- `test_selection_change_bumps_slice_generation`
- `test_stale_refresh_dropped_when_file_changes_during_load`
- `test_raster_viewer_plotly_config_enables_doubleclick_reset`
- Updated slice/refresh tests to set `current_selection` and matching `z`/`t` for
  the expanded stale-context checks.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_primary_image_view.py -q
uv run pytest tests/nicewidgets/test_plotly_viewer_state.py::test_raster_viewer_plotly_config_enables_doubleclick_reset -q
uv run pytest tests/nicewidgets/test_plotly_viewer_square_plot.py::test_doubleclick_reset_applies_full_unpadded_extent -q
```

## Test results

- `tests/cloudscope/test_primary_image_view.py`: **25 passed**
- `test_raster_viewer_plotly_config_enables_doubleclick_reset`: **1 passed**
- `test_doubleclick_reset_applies_full_unpadded_extent`: **1 passed**

## Concerns or follow-ups

- **Low-res zoom after Z scrub (step 4)** is still expected until **ticket 128**:
  Path B reloads overview PNG via `set_data_from_pyramid` while the browser keeps
  zoomed axis ranges — accidental, not deterministic viewport preservation.
- **User GUI retest** required for steps **5** (double-click) and **8** (Z slider
  after file switch) only; step 4 low-res should log `full_image_png` / `image` trace
  at DEBUG until 128.
- Ticket **128** (`swap_plane`: atomic viewport + contrast + LUT) remains the
  correct fix for deterministic zoom preservation on Z/T scrub.
