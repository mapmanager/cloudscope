# Raster Viewer Flash Fix Report

## Files Changed

- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
- `src/nicewidgets/raster_viewer/frontend/roi_overlay.py`
- `src/cloudscope/views/primary_image_view.py`
- `tests/nicewidgets/test_plotly_viewer_square_plot.py`
- `tests/nicewidgets/test_plotly_roi_overlay.py`
- `tests/cloudscope/test_primary_image_view_handlers.py`
- `docs-dev/codex_tickets/123_raster_viewer_flash_fix_report.md`

## Summary of Implementation

- Moved ROI visual padding into the initial full Plotly figure update when the existing browser plot size is available, avoiding the unpadded render followed by a visible padded relayout.
- Kept the existing post-render visual-padding fallback for cases where the browser plot size is not available before the first update.
- Preserved the current padded display ranges when refreshing full PNG image traces for contrast/LUT updates, so contrast refreshes do not snap the viewport back to unpadded data bounds.
- Tracked the displayed primary image file/channel in `PrimaryImageView` and skipped full raster reloads for ROI-only selection changes, refreshing ROI and diameter overlays instead.
- Added a reusable padded display-range helper and used it for double-click full reset.
- Updated double-click reset to apply the reset response and padded full-extent layout through direct `Plotly.react` when plot size is known, avoiding NiceGUI `plot.update()` and the follow-up padding relayout.
- Updated the direct double-click reset path to refresh local layout from the reset response before applying padded ranges, so the browser receives the new reset `uirevision` instead of preserving a stale zoom.
- Updated ROI edit mode to set Plotly `dragmode` to `False` while a ROI shape is editable, then restore normal `'zoom'` dragmode when edit mode exits.
- Added a low-alpha fill only to the active editing ROI shape so its body is a reliable Plotly pointer target during shape dragging; idle and selected non-editing ROIs remain transparent.
- Superseded the visual-padding approach after the low-alpha editable ROI fill proved to address the ROI click/drag target directly.
- Removed the synthetic Plotly axis padding code and restored full-extent raster views to real unpadded image bounds.
- Simplified double-click reset back to a single full-response `plot.update()` path with a fresh `uirevision`, avoiding the padding-specific direct `Plotly.react` layout path.
- Final rollback pass restored `plotly_viewer.py` and `PrimaryImageView` to the pre-padding `eb076e7` behavior, removing the padding-era dragmode/layout experiments and the displayed-file/channel optimization.
- Kept only the editable ROI low-alpha fill as the minimal ROI hit-target fix.

## Tests Added or Modified

- Added a raster viewer test proving known plot size applies padded ranges before the first full Plotly update.
- Added a raster viewer test proving full PNG refreshes preserve the current display ranges.
- Added a raster viewer test proving double-click reset applies padded ranges without NiceGUI `plot.update()` or post-reset padding relayout when plot size is known.
- Extended the double-click reset test to prove the reset `Plotly.react` payload carries the new `uirevision`.
- Extended ROI edit-mode tests to prove edit mode disables Plotly drag zoom and restores it after exit.
- Added ROI overlay tests proving only the actively edited ROI gets the low-alpha body hit fill and that idle mode returns fills to transparent.
- Replaced padded-range tests with unpadded full-extent tests for initial load and double-click reset.
- Added a regression test proving double-click reset after a second file load uses the second file's full unpadded extent and fresh `uirevision`.
- Added primary image view tests proving ROI-only selection refreshes overlays without reloading raster pixels, while channel changes still reload.
- Removed test expectations for the reverted dragmode relayout and displayed-file/channel optimization.
- Kept ROI overlay tests proving the active editing ROI gets low-alpha fill and idle fills return to transparent.

## Exact Test Commands Run

```bash
uv run pytest tests/nicewidgets/test_plotly_viewer_square_plot.py tests/nicewidgets/test_plotly_viewer_state.py
uv run pytest tests/cloudscope/test_primary_image_view.py tests/cloudscope/test_primary_image_view_handlers.py
uv run pytest tests/nicewidgets/test_plotly_viewer_square_plot.py tests/nicewidgets/test_plotly_viewer_state.py
uv run pytest tests/nicewidgets/test_plotly_viewer_square_plot.py tests/nicewidgets/test_plotly_viewer_state.py
uv run pytest tests/nicewidgets/test_plotly_viewer_square_plot.py tests/nicewidgets/test_plotly_viewer_state.py
uv run pytest tests/nicewidgets/test_plotly_viewer_square_plot.py tests/nicewidgets/test_plotly_roi_overlay.py
uv run pytest tests/nicewidgets/test_plotly_viewer_square_plot.py tests/nicewidgets/test_plotly_roi_overlay.py tests/nicewidgets/test_plotly_viewer_state.py tests/nicewidgets/test_plotly_viewer_x_range.py
uv run pytest tests/nicewidgets/test_plotly_viewer_square_plot.py tests/nicewidgets/test_plotly_roi_overlay.py tests/nicewidgets/test_plotly_viewer_state.py tests/nicewidgets/test_plotly_viewer_x_range.py tests/cloudscope/test_primary_image_view_handlers.py
```

## Test Results

- Initial raster viewer focused run failed once while developing the `_refresh_full_png()` preservation change; the test showed the implementation was still passing `display_axis_ranges=None`.
- Focused CloudScope primary image tests passed: `29 passed`.
- Raster viewer focused tests passed after the preservation fix: `74 passed`.
- Raster viewer focused tests passed again after restoring double-click reset behavior: `74 passed`.
- Raster viewer focused tests passed after the double-click optimized reset follow-up: `75 passed`.
- Raster viewer focused tests passed after the reset `uirevision` and ROI edit interaction follow-up: `22 passed`.
- Raster viewer focused tests passed after removing visual padding and keeping the ROI edit hit-fill/dragmode fix: `90 passed`.
- Combined focused rollback test run initially failed due to the NiceGUI test stub missing `run` after nicewidgets tests populated `sys.modules`; the test stub was updated and the focused run then passed: `104 passed`.
- IDE diagnostics reported no linter errors for edited files.

## Concerns or Follow-ups

- Browser MCP visual verification was not run for the final implementation. The fix is covered by focused source-level tests, and browser verification can be done separately if desired.
- Source history shows Plotly `dragmode='zoom'` predated the visual-padding work; the padding change appears to have exposed the ROI edit hit-target/dragmode weakness rather than introducing that default.
- The report file is under ignored `docs-dev/`, so Git may not show it in normal status output even though it has been updated on disk.
- Browser verification is still recommended after this rollback because the original report was about interactive Plotly/NiceGUI timing and visual behavior.
