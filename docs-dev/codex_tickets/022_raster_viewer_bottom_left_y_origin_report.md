# Ticket 022 — Raster viewer bottom-left y origin

## Summary

Changed the NiceWidgets Plotly raster viewer to display y-axis coordinates with a
bottom-left origin while keeping the existing backend image transpose behavior.

The Phase 0 spike (`nicegui_y_axis_demo.py`) showed that Plotly heatmap and image
traces both honor the axis flip consistently. The apparent PNG mismatch came
from the visual interpretation of the `Greys` colorscale rather than from a
different coordinate mapping, so the production change is limited to Plotly
axis-range direction.

## Files changed

- `src/nicewidgets/raster_viewer/frontend/plotly_coord_transform.py`
  - Renamed `row_col_to_plot_y_range_layout` to `row_col_to_plot_y_range`.
  - Changed y-axis ranges from high-to-low to low-to-high.
  - Updated docstrings to describe the bottom-left display origin.
- `src/nicewidgets/raster_viewer/frontend/plotly_protocol.py`
  - Updated figure building and relayout fallback parsing to use the renamed
    bottom-up y-range helper.
- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
  - Updated range-pinning and programmatic axis setters to write y ranges
    low-to-high.
  - Updated the no-data scaffold figure to use `[0.0, 1.0]` for y.
  - Cleaned small type/lint warnings in touched code.
- `src/nicewidgets/raster_viewer/backend/image_model.py`
  - Updated `RasterGridSpec` documentation for the new y-axis convention.
- `src/nicewidgets/raster_viewer/demo/nicegui_y_axis_demo.py`
  - Added in Phase 0 as the permanent Plotly y-axis behavior spike/demo.
  - Updated wording to label top-down and bottom-up cases without referring to
    the old top-down behavior as current.
- `tests/nicewidgets/test_plotly_viewer_state.py`
  - Updated transform, relayout, and range-pinning expectations.
  - Added a regression test that y ranges are low-to-high.
- `src/nicewidgets/raster_viewer/tests/frontend/test_plotly_coord_transform.py`
  - Updated expectations and added low-to-high y-range coverage.
- `src/nicewidgets/raster_viewer/tests/frontend/test_plotly_protocol.py`
  - Updated bottom-up y-range expectations.
- `src/nicewidgets/raster_viewer/tests/frontend/test_plotly_viewer.py`
  - Updated imports to the in-repo `nicewidgets.raster_viewer` package path.
  - Replaced stale `pytest.mark.asyncio` usage with `asyncio.run`.
- `src/nicewidgets/raster_viewer/tests/backend/test_pyramid.py`
  - Updated imports to the in-repo `nicewidgets.raster_viewer` package path.
- `src/nicewidgets/raster_viewer/tests/backend/test_raster_service.py`
  - Updated imports to the in-repo `nicewidgets.raster_viewer` package path.

## Tests added or modified

- Added bottom-left y-origin regression coverage for `PlotlyCoordTransform`.
- Updated Plotly figure and relayout tests to expect y-axis ranges ordered
  `[y_lo, y_hi]`.
- Updated package-local raster viewer tests so they run against the current
  in-repo package path.

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_viewer_state.py src/nicewidgets/raster_viewer/tests/frontend/test_plotly_coord_transform.py src/nicewidgets/raster_viewer/tests/frontend/test_plotly_protocol.py src/nicewidgets/raster_viewer/tests/frontend/test_plotly_viewer.py
uv run pytest tests/nicewidgets src/nicewidgets/raster_viewer/tests
uv run pytest tests/nicewidgets
uv run pytest src/nicewidgets/raster_viewer/tests
uv run python -m py_compile src/nicewidgets/raster_viewer/demo/nicegui_y_axis_demo.py
```

## Test results

Focused raster viewer command after fixes:

```text
59 passed in 0.08s
```

Main NiceWidgets tests:

```text
194 passed, 2 warnings in 0.65s
```

Package-local raster viewer tests:

```text
31 passed in 0.45s
```

Demo syntax check:

```text
py_compile completed with exit code 0
```

The combined `tests/nicewidgets src/nicewidgets/raster_viewer/tests` command
failed during collection because pytest imported two files named
`test_raster_service.py` under the same module name. Running those two test
roots separately passed.

The `tests/nicewidgets` warnings are the pre-existing all-NaN raster-service
warnings.

## Concerns or follow-ups

- Manual browser verification after this refactor was not rerun in this pass.
  Phase 0 visual verification was completed before implementation, and the
  automated tests now cover the expected bottom-up y-range behavior.
- The `Greys` colorscale visual interpretation differs between heatmap and PNG
  paths. That is separate from the coordinate-system change and should be
  handled in a follow-up ticket if consistent visual polarity is desired.
