# Acq analysis plot — PlotlyPlotWidget swap (Phase 3)

## Files changed

- `src/cloudscope/views/acq_analysis_plot_view.py`
- `src/cloudscope/events/x_range.py` (doc comment only)
- `tests/cloudscope/test_acq_analysis_plot_view.py`
- `docs-dev/codex_tickets/acq_analysis_plot_plotly_phase3_report.md`

## Summary

Replaced ``EChartWidget`` with ``PlotlyPlotWidget`` in ``AcqAnalysisPlotView``.
Event bus wiring unchanged. Plot refresh uses ``set_series`` + ``plot.events``;
empty state clears traces and event overlays.

## Tests modified

- ``tests/cloudscope/test_acq_analysis_plot_view.py`` — fake chart uses
  ``set_series`` / ``clear_events``

## Test commands run

```bash
uv run pytest tests/cloudscope/test_acq_analysis_plot_view.py tests/cloudscope/test_x_range_view_wiring.py -q
```

## Test results

42 passed.

## Follow-ups

- ~~Optional: wire ``ThemeChanged`` like ``SumIntensityPlotView``~~ (done)
- EChart package remains for now (other tests); no CloudScope consumer
