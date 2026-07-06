# 102 — Disable PlotlyPlotWidget internal grid lines

## Files changed

- `src/nicewidgets/plotly_plot/widget.py`
- `tests/nicewidgets/test_plotly_plot_widget.py`

## Summary of implementation

`PlotlyPlotWidget` no longer ties `xaxis.showgrid` / `yaxis.showgrid` to the axis-label
visibility toggle. Grid lines inside the plot area stay off by default when axis
labels are shown.

Future work: context-menu toggles for horizontal and vertical grid lines.

## Tests added or modified

- `test_axis_labels_on_keeps_plot_grid_lines_off`

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_plot_widget.py -q
```

## Test results

42 passed in 0.69s

## Concerns or follow-ups

- Raster viewer (`PlotlyRasterViewer`) still shows grid when axis labels are on.
- Grid line context-menu toggles deferred to a follow-up ticket.
