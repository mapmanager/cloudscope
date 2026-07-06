# 101 — Sum-intensity right y-axis label visibility

## Files changed

- `src/nicewidgets/plotly_plot/widget.py`
- `src/cloudscope/views/sum_intensity_plot_view.py`
- `tests/nicewidgets/test_plotly_plot_widget.py`
- `tests/cloudscope/test_sum_intensity_plot_view.py`

## Summary of implementation

`PlotlyPlotWidget` now shows right y-axis decorations (title, ticks, line, and dual
right margin) only when axis labels are enabled **and** at least one right-axis
trace or scatter is **visible**. Invisible right-axis series still bind to `y2` so
Plotly scaling works when toggled on.

Added `set_y2_label()` and optional `on_series_visibility_changed` callback so
callers can update the y2 title when context-menu toggles change.

`SumIntensityPlotView` applies y2 label rules after each plot refresh and on
derivative/diameter visibility toggles:

- Neither visible → empty y2 label / no decorations
- Derivative visible (alone or with diameter) → `d(df/f0)/dt (1/s)`
- Diameter only → `Diameter (um)` from `DiameterAnalysis.get_plot_data()`

## Tests added or modified

- `tests/nicewidgets/test_plotly_plot_widget.py`: hidden right-axis trace hides
  decorations; toggle shows/hides decorations and margin
- `tests/cloudscope/test_sum_intensity_plot_view.py`: y2 label for hidden,
  derivative-only, and diameter-only cases

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_plot_widget.py tests/cloudscope/test_sum_intensity_plot_view.py -q
```

## Test results

65 passed in 1.47s

## Concerns or follow-ups

- Home-page x-axis visual alignment across the three stacked Plotly figures is
  deferred (plan step 2).
- Browser verification of y2 label behavior in the live app was not run in this
  pass; unit tests cover the widget and view logic.
