# 093 Plotly plot placeholder empty state

## Files changed

- `src/nicewidgets/plotly_plot/widget.py`
- `src/cloudscope/views/acq_analysis_plot_view.py`
- `src/cloudscope/views/sum_intensity_plot_view.py`
- `tests/nicewidgets/test_plotly_plot_widget.py`
- `tests/cloudscope/test_acq_analysis_plot_view.py`
- `tests/cloudscope/test_sum_intensity_plot_view.py`

## Summary of implementation

Added a generic caller-driven empty-state API to `PlotlyPlotWidget`:

- `show_legend: bool = True` constructor kwarg (avoids legend flash on init)
- `set_placeholder_text(message: str | None)` — centered overlay on the plot area
- `placeholder_text` read-only property
- `set_series()` with non-empty data auto-hides the placeholder

The plotly element is now `_plot_element`; `container` is the outer relative wrapper
views already size with flex classes.

**AcqAnalysisPlotView:** `show_legend=False` on init; `_clear_chart(message)` sets
placeholder text from `_empty_message()` when no analysis plot data is available.

**SumIntensityPlotView:** removed external `_status_label` and summary footer; empty
and error states use `set_placeholder_text()`; successful refresh clears placeholder.
`sum_intensity_analysis_view.py` was not modified.

## Tests added or modified

- Plotly: `test_init_show_legend_false_builds_without_legend`,
  `test_set_placeholder_text_shows_and_hides_overlay`,
  `test_set_series_with_data_clears_placeholder`; extended fake UI fixture
- Acq plot view: placeholder assertion on empty refresh
- Sum-intensity plot view: placeholder assertions replace `_status_label` checks

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_plot_widget.py tests/cloudscope/test_acq_analysis_plot_view.py tests/cloudscope/test_sum_intensity_plot_view.py -q
```

## Test results

82 passed in 1.58s

## Concerns or follow-ups

- Browser verification of centered placeholder styling in dark/light themes was not
  run in this pass; unit tests cover API behavior only.
