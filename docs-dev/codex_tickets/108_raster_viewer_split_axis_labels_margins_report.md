# 108 — Raster viewer split axis labels and shared Plotly margins

## Files changed

- `src/nicewidgets/plotly_axis_layout.py` (new)
- `src/nicewidgets/plotly_plot/widget.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_display_options.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_context_menu.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_protocol.py`
- `src/cloudscope/views/primary_image_view.py`
- `tests/nicewidgets/test_plotly_raster_context_menu.py`
- `tests/test_plotly_raster_context_menu.py`

## Summary of implementation

- Extracted shared axis decoration and margin helpers into
  `nicewidgets/plotly_axis_layout.py` (`PLOTLY_AXIS_LABEL_FONT_SIZE`,
  `any_axis_labels_visible`, `apply_axis_decorations`, `resolve_plot_layout_margins`).
- Refactored `plotly_plot/widget.py` to import shared helpers.
- Raster viewer now mirrors plotly_plot:
  - Independent `show_x_axis_labels` / `show_y_axis_labels`
  - `set_x_axis_labels_visible` / `set_y_axis_labels_visible`
  - Split context-menu toggles
  - OR-based margin profile selection
  - Shared `resolve_plot_layout_margins` fallback (replaced raster-local margin tables)
  - Grid lines stay off when axis labels are on (plotly_plot pattern)
  - Font size 11 on axis title and tick labels
- `primary_image_view` initializes raster with `show_x_axis_labels=True`,
  `show_y_axis_labels=False` and existing home stack margin profile.

## Tests added or modified

- Updated raster context-menu tests for split toggles, shared margins, grid off, font size.
- Updated legacy `tests/test_plotly_raster_context_menu.py` for new display-option fields.

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_plot_widget.py tests/nicewidgets/test_plotly_raster_context_menu.py tests/test_plotly_raster_context_menu.py tests/cloudscope/test_home_stack_layout_margins.py -q
```

## Test results

75 passed.

## Concerns or follow-ups

- Per-edge margin refinement still deferred: OR-based profile may reserve left
  margin when only x labels are visible (home stack uses fixed `l=60` profile).
- Future ticket: independent X/Y grid-line toggles for raster viewer and plotly_plot.
