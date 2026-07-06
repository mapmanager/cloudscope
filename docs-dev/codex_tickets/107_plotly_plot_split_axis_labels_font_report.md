# 107 — Plotly plot split axis labels and font size

## Files changed

- `src/nicewidgets/plotly_plot/display_options.py`
- `src/nicewidgets/plotly_plot/context_menu.py`
- `src/nicewidgets/plotly_plot/widget.py`
- `src/cloudscope/views/acq_analysis_plot_view.py`
- `src/cloudscope/views/sum_intensity_plot_view.py`
- `tests/nicewidgets/test_plotly_plot_widget.py`

## Summary of implementation

- Replaced single `show_axis_labels` / `set_axis_labels_visible` with independent
  `show_x_axis_labels` / `show_y_axis_labels` display options and
  `set_x_axis_labels_visible` / `set_y_axis_labels_visible` public APIs.
- Context menu now offers **X Axis Labels** and **Y Axis Labels** toggles; removed
  combined **Axis Labels** item.
- Secondary right y-axis (`yaxis2`) decorations follow `show_y_axis_labels` when
  a visible right-axis series is present.
- Margin profile selection uses OR of x/y visibility (`show_x or show_y`).
- Added module constant `_PLOTLY_PLOT_AXIS_LABEL_FONT_SIZE = 11` applied to axis
  title and tick fonts on xaxis, yaxis, and yaxis2 via `_apply_axis_label_font`
  / `_apply_axis_decorations`.
- CloudScope `acq_analysis_plot_view` and `sum_intensity_plot_view` initialize
  plots with `show_x_axis_labels=True`, `show_y_axis_labels=False`.

## Tests added or modified

- Updated existing axis-label tests for split toggles.
- Added `test_init_axis_label_visibility_kwargs`.
- Added `test_x_and_y_axis_labels_toggle_independently`.
- Added `test_axis_label_font_size_is_explicit`.

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_plot_widget.py -q
```

## Test results

51 passed.

## Concerns or follow-ups

- Per-edge margin refinement (left only when Y on, bottom only when X on) deferred;
  current OR-based binary margin profile may reserve left margin when only x labels
  are visible in the home stack.
