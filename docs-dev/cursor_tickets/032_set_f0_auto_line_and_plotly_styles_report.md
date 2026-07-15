# 032 — Set F0 auto line, dual H-lines, Plotly measurement styles

## Summary of implementation

Follow-up to ticket 031 Set F0:

1. **AcqStore** `SumIntensityAnalysis.get_percentile_f0_baseline(percentile=None)` recomputes auto F0 from the stored detrended normalized intensity trace (same rules as percentile baseline), including after a manual run.
2. **nicewidgets** `PlotlyPlotWidget.add_measurement_line` gains `editable`, `color`, `dash`, `show_legend`, and `legend_label`. Default color is theme `font_color` (readable in dark mode). Non-editable lines ignore drag relayout callbacks. Shape `name` + `showlegend` support Plotly legend entries.
3. **CloudScope Set F0 mode** shows:
   - Toolbar: **Auto F0** + **Manual F0** labels
   - Plot: non-editable dotted cyan **Auto F0** line + editable solid yellow **Manual F0** line (both legend-enabled)
   - Accept still commits only manual F0 (`baseline_method=manual`, `manual_f0_baseline`)

### Explicitly deferred (future tickets)

- Persist `percentile_f0_baseline` in summary
- Toolbar `baseline_percentile` control + **Compute auto F0** button
- Two commit actions (Accept manual vs Accept percentile method)
- Idle-toolbar / F0 line over df/f0 plot (units differ; not scientifically valid)

## Files changed

- `src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_analysis.py`
- `src/nicewidgets/plotly_plot/models.py`
- `src/nicewidgets/plotly_plot/widget.py`
- `src/cloudscope/views/sum_intensity_plot_toolbar.py`
- `src/cloudscope/views/sum_intensity_plot_view.py`
- `tests/acqstore/test_sum_intensity_analysis.py`
- `tests/nicewidgets/test_plotly_plot_widget.py`
- `tests/cloudscope/test_sum_intensity_plot_view.py`
- `docs-dev/cursor_tickets/032_set_f0_auto_line_and_plotly_styles_report.md`

## Tests added or modified

- AcqStore: percentile accessor matches run F0; works after manual run; override percentile
- Plotly: style/legend shape options; non-editable ignores drag
- Plot view: enter mode adds both lines with styles; exit removes both

## Exact test commands run

```bash
uv run pytest \
  tests/acqstore/test_sum_intensity_analysis.py \
  tests/nicewidgets/test_plotly_plot_widget.py \
  tests/cloudscope/test_sum_intensity_plot_view.py
```

## Test results

```text
102 passed, 1 warning in 0.53s
```

## Concerns or follow-ups

- Legend visibility depends on the sum-intensity plot’s legend display option (often off by default); when the user enables legend, Auto/Manual F0 shapes should list.
- Browser verification of shape legend + dark-mode line colors recommended when convenient (unit tests cover shape dicts only).
