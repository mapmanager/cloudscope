# Ticket 013 — PlotlyRasterViewer math/state tests

## Files changed

- `tests/nicewidgets/test_plotly_viewer_state.py` — new file with 44 tests
- `docs/codex_tickets/013_plotly_viewer_state_tests_report.md` (this report)

## Summary of implementation

`PlotlyRasterViewer` and its math helpers (`plotly_coord_transform`,
`plotly_protocol`) previously had only one test (the
`set_data_clears_trace_overlays` smoke test). The viewer is challenging to
unit-test because most public methods push JavaScript through `ui.plotly` and
require a live NiceGUI client. This ticket adds tests for everything that can
be exercised headlessly:

- `PlotlyCoordTransform` round-trip and clipping behavior, and
  `full_row_col_bounds`.
- `merge_partial_relayout` fills missing x/y, keeps existing ranges, and
  recognizes bracketed (`xaxis.range[0]`) keys.
- `plotly_protocol.parse_relayout_payload` honors list, bracket, and
  fallback paths.
- `plotly_protocol.build_plotly_figure` covers both `image_png` and
  `heatmap_z` modes, and raises when heatmap z is missing.
- `PlotlyRasterViewer` initial state (`has_data`, `plot`, `current_bounds`,
  `figure`).
- Static helpers: `_new_uirevision` uniqueness, `_display_style` defaults,
  `_js_plotly_graph_div` early return, `_layout_pin_xy_ranges` writes
  pinned axes, `_heatmap_trace_active`/`_image_trace_active` return False
  without a plot.
- `_build_initial_figure` returns the empty scaffold without data and a
  full figure after `set_data`.
- `set_data` resets contrast window, colorscale, and clears trace overlays.
- ROI overlay state: `set_rois`, `add_roi`, `delete_roi`, `select_roi`,
  and tolerance to a non-list `layout.shapes`.
- Trace overlay state: `set_trace_overlays`, `delete_trace_overlay`,
  `clear_trace_overlays`, and tolerance to a non-list `data`.
- `request_from_plotly` raises before `set_data` and returns a
  `ViewRequest` after it.
- `apply_response`, `set_axis_ranges`, `set_x_axis_range`,
  `set_heatmap_contrast`, and `set_heatmap_colorscale` raise the expected
  `RuntimeError` when the viewer was never built or has no active trace.
- Async event handlers (`_on_plotly_doubleclick`, `_on_plotly_autosize`,
  `_on_plotly_relayout`) early-return without service / unrelated args.

## Tests added or modified

44 new tests in `tests/nicewidgets/test_plotly_viewer_state.py`.

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_viewer_state.py -q
uv run pytest tests/nicewidgets/ \
    --cov=nicewidgets.raster_viewer.frontend.plotly_viewer \
    --cov=nicewidgets.raster_viewer.frontend.plotly_coord_transform \
    --cov=nicewidgets.raster_viewer.frontend.plotly_protocol \
    --cov-report=term-missing -q
```

## Test results

- 44 / 44 new tests passing
- 157 / 157 tests passing across `tests/nicewidgets/`
- Coverage of focus modules:
  - `plotly_coord_transform.py`: 55% → **100%**
  - `plotly_protocol.py`: 55% → **98%** (one line: an `else` raise that is
    unreachable through public API)
  - `plotly_viewer.py`: 41% → **63%**

## Concerns or follow-ups

- Remaining uncovered lines in `plotly_viewer.py` belong to methods that
  push JavaScript through `self._plot.client.run_javascript(...)` (overlay
  redraws, axis-range setters, doubleclick/relayout JS path, viewport-size
  fetch). These would require either a live NiceGUI client or a substantial
  fake of `Element`/`client` to test meaningfully. Out of scope for this
  ticket.
