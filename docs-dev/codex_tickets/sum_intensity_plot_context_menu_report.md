# Sum intensity plot context menu report

## Files changed

- `src/nicewidgets/plotly_plot/widget.py`
- `src/nicewidgets/plotly_plot/models.py`
- `src/nicewidgets/plotly_plot/display_options.py` (new)
- `src/nicewidgets/plotly_plot/context_menu.py` (new)
- `src/nicewidgets/plotly_plot/context_menu_guards.py` (new)
- `src/cloudscope/views/sum_intensity_plot_view.py`
- `scripts/nicewidgets/try_plotly_plot_widget.py`
- `tests/nicewidgets/test_plotly_plot_widget.py`
- `tests/cloudscope/test_sum_intensity_plot_view.py`

## Summary of implementation

### Plot title / subtitle removal

Removed layout title from `PlotlyPlotWidget` and disabled Plotly `config.edits` for
title, axis, and legend text so the editable subtitle placeholder no longer appears.

### Right-click context menu (`PlotlyPlotWidget`)

Added a raster-viewer-style context menu with:

- **Series toggles** (check-prefix labels): derivative, five peak-width traces, Onsets,
  and Peaks scatters. `df/f0 signal` stays always visible and is not listed.
- **Display options** (persist for the session across file/channel/ROI refresh):
  Axis Labels, Plotly Toolbar, Hover Info.
- **Copy To Clipboard** — desktop uses native PNG clipboard; browser uses shared
  Plotly PNG clipboard helper from the raster viewer.

### Visibility persistence (C4 decision)

Trace/scatter toggle choices are stored on the widget and **preserved across**
`_refresh_plot()` / selection changes until page reload. Menu defaults apply only on
first registration. Display chrome preferences are also preserved across refresh.

### SumIntensityPlotView

Registers sum-intensity menu items at plot creation. `_trace_data` / `_scatter_data`
apply stored visibility when building series for `set_series()`.

## Tests added or modified

- `tests/nicewidgets/test_plotly_plot_widget.py` — no layout title, series visibility
  persistence across `set_series`, scatter toggle restyle
- `tests/cloudscope/test_sum_intensity_plot_view.py` — menu defaults (derivative off,
  width 50 on, scatters on), visibility preserved across selection change

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_plot_widget.py tests/cloudscope/test_sum_intensity_plot_view.py -q
```

## Test results

31 passed in 1.80s

## Concerns or follow-ups

- Browser verification of context menu items and Copy To Clipboard (desktop + web) was
  not completed in this pass; recommend manual or Cursor browser MCP check with loaded
  sum-intensity data.
- Incremental `add_trace` / `plot_scatter` paths honor visibility when names are
  registered; callers that bypass menu registration still default to visible.
