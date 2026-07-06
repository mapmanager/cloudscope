# Ticket 009 — PrimaryImageView handler tests

## Files changed

- `tests/cloudscope/test_primary_image_view_handlers.py` — new file with 14 tests
- `docs/codex_tickets/009_primary_image_view_handler_tests_report.md` (this report)

## Summary of implementation

`PrimaryImageView` previously had targeted coverage on `_load_plane_payload`,
`raster_grid_spec_from_image_header`, the ROI overlay helpers, and BaseView
identity. The handler branches that route ROI / diameter / analysis-completion
events into the viewer were uncovered. A simple `FakeViewer` exposes
`set_rois`, `select_roi`, `clear_trace_overlays`, and `set_trace_overlays`
so each handler path can be asserted on without a real Plotly element.

New tests cover:

- `_refresh_roi_overlays`: clears viewer ROI list when acq_image or grid is
  missing; pushes converted overlays and selects the current ROI id when
  both are present.
- `_refresh_diameter_trace_overlays`: clears overlays when there is no acq
  image / grid / channel / ROI / diameter analysis / non-rect ROI; pushes
  converted overlays when a diameter analysis with a visible trace exists.
- `_on_analysis_completed`: ignores non-DIAMETER kinds and mismatched
  selections; refreshes overlays only for DIAMETER on the current file +
  channel + ROI.
- `_on_roi_changed`: refreshes both ROI and diameter overlays when the
  changed file matches the current selection; no-op when file ids differ
  or current file is None.
- `roi_local_traces_to_plotly_overlays`: offsets ROI-local coords by the
  ROI top-left + grid spacing; filters invisible traces and traces with
  empty x.
- `on_primary_selection_changed` and `refresh_from_state` delegate to
  `_refresh_raster_from_current_selection`.

## Tests added or modified

14 tests in the new file `tests/cloudscope/test_primary_image_view_handlers.py`.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_primary_image_view_handlers.py -q
uv run pytest tests/cloudscope/test_primary_image_view.py tests/cloudscope/test_primary_image_view_roi_overlay.py tests/cloudscope/test_primary_image_view_handlers.py tests/cloudscope/test_primary_image_diameter_overlay.py --cov=cloudscope.views.primary_image_view --cov-report=term-missing -q
```

## Test results

- 14 passed (and combined: 23 passed)
- `primary_image_view.py` coverage: **41% → 65%** (189 statements, 67 missed)
- Remaining missed lines are the async/io path
  (`_refresh_raster_from_current_selection`, `_refresh_raster_async`),
  `_run_ui` re-marshaling, `build()`, and the `_load_plane_payload`
  branch that reads from a real AcqImage (covered indirectly by the
  fake header tests).

## Concerns or follow-ups

- An `asyncio.run`-based test of `_refresh_raster_async` could close another
  10-20 lines.
