# 033 User Edit ROI Report

## Files Changed

- `src/nicewidgets/raster_viewer/frontend/roi_overlay.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
- `src/cloudscope/events/roi.py`
- `src/cloudscope/controllers/roi_controller.py`
- `src/cloudscope/views/primary_image_view.py`
- `tests/cloudscope/test_roi_controller.py`
- `src/nicewidgets/raster_viewer/tests/frontend/test_plotly_viewer.py`
- `docs/codex_tickets/033_user_edit_roi_report.md`

## Summary Of Implementation

- Added Plotly rectangle ROI shape edit support to `PlotlyRasterViewer`, gated by `set_roi_editing(enabled, roi_id)`.
- Kept raw Plotly `shapes[N].x0/x1/y0/y1` relayout parsing inside `nicewidgets` and emitted typed ROI preview callbacks to CloudScope.
- Added `RoiEditPreviewChanged` so CloudScope can stage preview bounds separately from canonical ROI state.
- Updated `PrimaryImageView` to convert Plotly physical coordinates to acqstore `RectRoiBounds`, update draft overlays, and restore canonical overlays when edit mode exits.
- Updated `RoiController` to cache staged edit bounds, commit on OK, cancel without mutation, support full-width/full-height staged previews, and confirm before removing dependent analyses.

## Tests Added Or Modified

- Updated ROI controller tests from placeholder assertions to commit/cancel/confirmation/full-extent preview behavior.
- Added Plotly raster viewer tests for editable ROI shape generation and shape relayout preview emission.

## Exact Test Commands Run

```bash
uv run pytest tests/cloudscope/test_roi_controller.py src/nicewidgets/raster_viewer/tests/frontend/test_plotly_viewer.py
```

```bash
uv run pytest tests/cloudscope/test_primary_image_view.py tests/cloudscope/test_primary_image_view_handlers.py tests/cloudscope/test_primary_image_view_roi_overlay.py tests/cloudscope/test_roi_controller.py src/nicewidgets/raster_viewer/tests/frontend/test_plotly_viewer.py
```

## Test Results

- `18 passed in 0.43s`
- `48 passed in 0.98s`

## Follow-Up: Full-Width / Full-Height Axis Mapping Fix

- Swapped the dimension mapping in `RoiController._stage_full_extent_edit` so the
  toolbar buttons match the on-screen axes: visual width = plot-x = `dim0` (rows),
  visual height = plot-y = `dim1` (cols). Full-width now fills `dim0`; full-height
  now fills `dim1`. See `docs/acqstore_kymograph_axes.md`.
- Updated `test_roi_controller_full_extent_edit_intents_publish_previews` expected
  preview bounds for the corrected mapping.
- Command: `uv run pytest tests/cloudscope/test_roi_controller.py` → `8 passed in 0.07s`.

## Concerns Or Follow-Ups

- Browser-level manual verification is still recommended because Plotly shape dragging behavior depends on runtime Plotly/NiceGUI event payloads.
- The implementation handles the documented `shapes[N].x0/x1/y0/y1` relayout payloads. If Plotly emits whole-shape-list payloads for a browser/version combination, the widget parser may need a small additional branch.
