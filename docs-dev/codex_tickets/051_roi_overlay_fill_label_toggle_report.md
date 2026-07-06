# 051 Raster Viewer ROI Fill / Label Cosmetics Report

## Files changed

- `src/nicewidgets/raster_viewer/frontend/roi_overlay.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_display_options.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_context_menu.py`
- `tests/nicewidgets/test_plotly_roi_overlay.py`
- `tests/nicewidgets/test_plotly_raster_context_menu.py`
- `docs-dev/codex_tickets/051_roi_overlay_fill_label_toggle_report.md`

## Summary of implementation

1. **Transparent ROI fill (all states).** Changed the DRY `RectRoiStyleConfig`
   defaults so `fill_color`, `selected_fill_color`, and `editing_fill_color`
   are `rgba(0, 0, 0, 0)`. The `fillcolor` key is still emitted by
   `_roi_to_shape`, keeping the styling driven by the single config and leaving
   ROI rectangles outline-only.
2. **Label moved to top-left.** `_roi_to_shape` now emits
   `label = {'text': ..., 'textposition': 'top left'}` instead of the Plotly
   default centered label.
3. **New 'ROI Labels' context menu toggle.**
   - Added `show_roi_labels: bool = True` to
     `PlotlyRasterViewerDisplayOptions`.
   - Added `PlotlyRasterViewer.set_roi_labels_visible(...)` mirroring
     `set_roi_overlays_visible`, plus a `_set_roi_label_visibility(...)` helper
     that blanks managed ROI shape label text when labels are disabled. The
     helper is invoked from `_sync_roi_shapes_to_plotly_dict` and
     `_apply_display_options_to_plotly_dict`, matching the existing
     `_set_roi_shape_visibility` pattern (labels are re-emitted by the overlay
     layer on every sync, so re-enabling restores the text).
   - Added an `ROI Labels` item to `PlotlyRasterViewerContextMenu.build()`
     directly after `ROIs`, and called `set_enabled(options.show_rois)` so the
     item is shown but disabled while ROIs are hidden. The menu is rebuilt on
     every right-click, so the enabled state always reflects the current
     `show_rois` value.

## Tests added or modified

- `tests/nicewidgets/test_plotly_roi_overlay.py`
  - `test_default_style_uses_transparent_fill_for_all_states`
  - `test_roi_shape_label_is_positioned_top_left`
- `tests/nicewidgets/test_plotly_raster_context_menu.py`
  - `test_show_roi_labels_defaults_to_true`
  - `test_roi_label_visibility_toggle_blanks_and_restores_label_text`

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_roi_overlay.py tests/nicewidgets/test_plotly_raster_context_menu.py
uv run pytest
```

## Test results

- Focused: `19 passed in 0.70s`
- Full suite: `1073 passed, 15 warnings in 3.83s`

## Concerns or follow-ups

- The context-menu `set_enabled(...)` wiring is UI-only and is not unit tested;
  the testable display-option and viewer logic (`show_roi_labels`,
  `set_roi_labels_visible`) is covered.
- Label visibility is implemented by blanking the Plotly shape `label.text`
  rather than removing the label dict, since the overlay layer rebuilds labels
  on each sync and re-enabling restores the original text.
