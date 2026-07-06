# 104 — Sum-intensity legend default off and scatter x-axis alignment

## Files changed

- `src/cloudscope/views/sum_intensity_plot_view.py`
- `src/nicewidgets/plotly_plot/widget.py`
- `tests/nicewidgets/test_plotly_plot_widget.py`

## Summary of implementation

**Legend default off:** `SumIntensityPlotView` constructs `PlotlyPlotWidget` with
`show_legend=False`.

**Scatter x-axis inset fix:** Visible scatter overlays (Onsets, Peaks, etc.) caused
Plotly to shift x=0 right after `set_series` because `Plotly.addTraces` expands
the displayed x range for marker padding while `set_x_axis_limits` skipped
relayout when the logical range was unchanged.

- `_reapply_x_axis_limits()` runs after `set_series` when a finite x range is set.
- Scatter traces set `cliponaxis=True` so markers at x=0 do not request negative-x
  padding during autorange.

## Tests added or modified

- `test_set_series_reapplies_x_axis_limits_when_range_unchanged`
- `test_scatter_trace_clips_markers_on_axis`

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_plot_widget.py tests/cloudscope/test_sum_intensity_plot_view.py -q
```

## Test results

70 passed in 1.52s

## Concerns or follow-ups

- When x-range is autorange (`None`, `None`), only `cliponaxis` limits marker
  padding; explicit shared x-range from `XRangeController` is the normal stack path.
