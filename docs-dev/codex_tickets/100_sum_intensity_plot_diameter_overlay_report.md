# 100 — Sum-intensity plot diameter overlay

## Files changed

- `src/cloudscope/views/sum_intensity_plot_view.py`
- `tests/cloudscope/test_sum_intensity_plot_view.py`

## Summary

Optional **Diameter** trace on the sum-intensity plot (`SumIntensityPlotView`), sourced from
`DiameterAnalysis.get_plot_data()` for the same file/channel/ROI. Context-menu toggle
(default off); visibility persists across selection changes via existing
`PlotlyPlotWidget` series visibility. Trace uses `yaxis2` (shared with derivative).
Sum-intensity analysis remains required for any plot display.

## Tests added or modified

- `test_get_selected_diameter_analysis_returns_matching_analysis`
- `test_refresh_plot_includes_diameter_trace_when_analysis_present`
- `test_refresh_plot_omits_diameter_trace_when_toggle_on_but_no_analysis`
- `test_refresh_plot_shows_diameter_when_toggle_on`
- `test_matching_analysis_completion_refreshes_plot` (SI + diameter)

## Test commands run

```bash
uv run pytest tests/cloudscope/test_sum_intensity_plot_view.py -q
```

## Test results

```
20 passed in 1.52s
```

## Concerns or follow-ups

- Derivative and diameter share one y2 axis/label when both visible (accepted scope).

## Follow-up (menu separation)

- `PlotlySeriesMenuItem.separator_before` — Diameter moved last among series toggles with separator before it.
