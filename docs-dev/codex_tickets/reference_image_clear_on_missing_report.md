# Reference image clear on missing report

## Files changed

- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
- `src/cloudscope/views/reference_image_view.py`
- `src/nicewidgets/raster_viewer/tests/frontend/test_plotly_viewer.py`
- `tests/cloudscope/test_reference_image_view.py`

## Summary of implementation

When no reference image is available (no file, no AcqStore reference, or load
failure), `ReferenceImageView` now calls `PlotlyRasterViewer.clear_data()`
instead of pushing a 2×2 placeholder through `set_data()`.

Added `PlotlyRasterViewer.clear_data()` to reset backend state and restore the
empty pre-data Plotly figure (`data: []`).

`_load_reference_plane_payload()` now returns
`(array, grid, message, is_real_reference)` with `None` array/grid when no
reference plane exists.

## Tests added or modified

- `test_clear_data_resets_viewer_to_empty_figure`
- Updated payload helper tests for empty vs real reference
- `test_refresh_reference_async_clears_viewer_when_no_reference`
- `test_refresh_reference_async_set_data_when_reference_exists`

## Exact test commands run

```bash
uv run pytest src/nicewidgets/raster_viewer/tests/frontend/test_plotly_viewer.py::test_clear_data_resets_viewer_to_empty_figure tests/cloudscope/test_reference_image_view.py -v
```

## Test results

12 passed in 1.27s

## Concerns or follow-ups

- CZI files still have no AcqStore `reference_image`; panel shows empty axes.
- Channel-swap alignment for reference view remains a separate follow-up.
