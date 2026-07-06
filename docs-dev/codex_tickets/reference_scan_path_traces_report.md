# Reference scan path traces

## Files changed

- `src/cloudscope/views/reference_image_view.py`
- `src/nicewidgets/raster_viewer/frontend/trace_overlay.py`
- `tests/cloudscope/test_reference_image_view.py`
- `tests/nicewidgets/test_plotly_trace_overlay.py`
- `docs-dev/codex_tickets/reference_scan_path_traces_report.md`

## Summary of implementation

- Added `scan_path_to_plotly_overlays()` in `ReferenceImageView` to read AcqStore
  `ReferenceImage.has_scan_path()` / `get_scan_path_plot()` and map pixel
  coordinates to Plotly physical axes (`plotly_x = y_pixels * dx`,
  `plotly_y = x_pixels * dy`).
- After reference raster `set_data` and contrast apply, the view now pushes a
  cyan `lines+markers` scan-path overlay via `PlotlyRasterViewer.set_trace_overlays()`.
- Extended `PlotlyTraceOverlayLayer` so `color` and `line_width` emit Plotly
  `line` styling when the trace mode includes lines (needed for cyan line color).
- Malformed scan paths fail fast with `ValueError`, surfaced through the existing
  reference refresh error path.

## Tests added or modified

- `tests/cloudscope/test_reference_image_view.py`
  - `test_scan_path_to_plotly_overlays_returns_empty_without_scan_path`
  - `test_scan_path_to_plotly_overlays_maps_pixels_to_plotly_coords`
  - `test_refresh_reference_async_set_trace_overlays_when_scan_path_exists`
- `tests/nicewidgets/test_plotly_trace_overlay.py`
  - `test_trace_overlay_lines_mode_emits_line_style`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_reference_image_view.py tests/nicewidgets/test_plotly_trace_overlay.py
```

## Test results

```
uv run pytest tests/cloudscope/test_reference_image_view.py tests/nicewidgets/test_plotly_trace_overlay.py -q
......................                                                   [100%]
22 passed in 1.61s
```

## Concerns or follow-ups

- Coordinate mapping should be verified visually in the running app; swap x/y if
  the scan path appears rotated or mirrored.
- `plotly_type='scattergl'` is intentional for now; inline TODO notes possibly
  switching back to `'scatter'`.
- Manual QA on real OIR/CZI files is left to the user.
