# 128 — Preserve viewport on Z/T scrub

## Files changed

- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
- `src/cloudscope/views/primary_image_view.py`
- `tests/cloudscope/test_primary_image_view.py`
- `tests/nicewidgets/test_plotly_viewer_state.py`
- `docs-dev/codex_tickets/128_preserve_viewport_on_zt_scrub_report.md`

## Summary of implementation

Added viewport-preserving slice reload for Z/T scrubs:

- **`PlotlyRasterViewer.get_viewport()`** — public API returning cached Plotly axis ranges.
- **`PlotlyRasterViewer.swap_slice_plane()`** — replaces backend plane/pyramid without resetting `uirevision`, contrast, or overlays; renders at the preserved viewport via `apply_response(..., display_axis_ranges=...)`.
- **Path B in `PrimaryImageView`** — Z/T scrubs call `swap_slice_plane` with `get_viewport()` instead of full `set_data_from_pyramid`.
- **`set_heatmap_style(preserve_viewport=...)`** — overview PNG re-encode after contrast apply on slice scrubs no longer resets zoom.

Path A (file/channel selection) still uses full `set_data_from_pyramid` reset.

## Tests added or modified

- `test_get_viewport_returns_last_display_ranges_after_set_data`
- `test_swap_slice_plane_preserves_zoomed_viewport`
- `test_slice_refresh_passes_preserved_viewport_to_viewer`
- Updated Path B mocks to use `swap_slice_plane` / `get_viewport`
- Updated `_FakeViewer.set_heatmap_style` for `preserve_viewport` kwarg

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_primary_image_view.py -q
uv run pytest tests/nicewidgets/test_plotly_viewer_state.py::test_get_viewport_returns_last_display_ranges_after_set_data tests/nicewidgets/test_plotly_viewer_state.py::test_swap_slice_plane_preserves_zoomed_viewport -q
```

## Test results

- `tests/cloudscope/test_primary_image_view.py`: **28 passed**
- nicewidgets viewport tests: **2 passed**

## Concerns or follow-ups

- Manual GUI verify: load file → zoom/pan → scrub Z/T → viewport should stay fixed; logs should show `swap_slice_plane: preserve viewport` (zoomed) or `full extent` (not zoomed).
- When zoomed to overview (`image` trace), contrast re-encode uses `preserve_viewport=True`; heatmap trace uses restyle (unchanged).
- Z/T planes share shape — clamp-to-bounds in `_clamp_display_axis_ranges` is defensive only.
