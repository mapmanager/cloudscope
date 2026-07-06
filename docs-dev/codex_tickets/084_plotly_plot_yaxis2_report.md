# Plotly plot widget — secondary y-axis (yaxis2)

## Files changed

- `src/nicewidgets/plotly_plot/models.py`
- `src/nicewidgets/plotly_plot/widget.py`
- `src/cloudscope/views/sum_intensity_plot_view.py`
- `tests/nicewidgets/test_plotly_plot_widget.py`
- `tests/cloudscope/test_sum_intensity_plot_view.py`
- `AGENTS.md` (ticket numbering guidance)
- `docs-dev/codex_tickets/084_plotly_plot_yaxis2_report.md`

## Summary

Extended ``PlotlyPlotWidget`` with optional ``layout.yaxis2`` for a single
right-hand y-axis. Traces, scatters, and horizontal measurements accept
``y_axis="left"`` (default) or ``y_axis="right"``. Only traces and scatters
create or remove ``yaxis2``; right-axis measurements fail fast when
``yaxis2`` is absent. ``MeasurementChangeEvent`` carries ``y_axis`` so
callers know which scale a drag used. Axis-label toggle and theme sync
include ``yaxis2``; dual-axis label mode widens the right margin.

``SumIntensityPlotView`` plots ``Derivative of df/f0`` on the right axis with
``y2_label="d(df/f0)/dt (1/s)"``.

## Tests added or modified

- ``tests/nicewidgets/test_plotly_plot_widget.py`` — yaxis2 lifecycle, mixed
  ``set_series``, right scatter, gated right measurement, axis-label margin
- ``tests/cloudscope/test_sum_intensity_plot_view.py`` — derivative trace
  ``y_axis="right"``

## Test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_plot_widget.py tests/cloudscope/test_sum_intensity_plot_view.py -q
```

## Test results

49 passed.

## Follow-ups

- Extract ``PlotlyTracesApi`` sub-API once axis CRUD is stable in production
- Wire sum-intensity derivative-threshold measurement on ``y_axis="right"``
- Programmatic ``y2`` limits only if a view needs synced right-axis range
