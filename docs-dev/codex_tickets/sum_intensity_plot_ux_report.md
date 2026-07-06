# Sum intensity plot UX report

## Files changed

- `src/nicewidgets/plotly_plot/widget.py`
- `src/cloudscope/views/sum_intensity_plot_view.py`
- `src/cloudscope/pages/home_page.py`
- `src/cloudscope/views/splitter_manager.py`
- `src/cloudscope/app_config.py`
- `tests/nicewidgets/test_plotly_plot_widget.py`
- `tests/cloudscope/test_sum_intensity_plot_view.py`
- `tests/cloudscope/test_splitter_manager.py`
- `tests/cloudscope/test_app_config_splitters.py`

## Summary of implementation

### Home page layout

Added a nested `ANALYSIS_SUM_INTENSITY` splitter inside the analysis column so the 1D
kymograph plot and sum intensity plot each occupy a resizable pane (default 58% / 42%).
Splitter values persist in `AppConfig` and participate in layout reset.

### PlotlyPlotWidget (`nicewidgets`)

- Added light/dark theme support via `theme` constructor arg, `set_theme()`, and
  `set_dark_mode()` using shared `plotly_theme` helpers.
- Moved legend to a horizontal layout below the plot (raster viewer pattern).
- Added `set_series()` to replace all traces and scatters in one browser update
  (`deleteTraces` + `addTraces` in a single JS block).

### SumIntensityPlotView

- Uses `set_series()` for refresh instead of incremental add/clear calls.
- Subscribes to `ThemeChanged` and resyncs theme from `dark_mode_provider` on
  `refresh_from_state()`.
- Receives `dark_mode` / `dark_mode_provider` from `HomePage` like other Plotly views.

## Tests added or modified

- `tests/nicewidgets/test_plotly_plot_widget.py` — theme, legend, `set_series` batching
- `tests/cloudscope/test_sum_intensity_plot_view.py` — batch refresh, theme wiring
- `tests/cloudscope/test_splitter_manager.py` — new splitter default
- `tests/cloudscope/test_app_config_splitters.py` — new persisted splitter field

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_plot_widget.py tests/cloudscope/test_sum_intensity_plot_view.py tests/cloudscope/test_splitter_manager.py tests/cloudscope/test_app_config_splitters.py -q
```

## Test results

49 passed in 1.56s

## Concerns or follow-ups

- Browser verification of splitter drag UX, dark-mode toggle, legend placement, and
  selection-change flicker should be done manually or via Cursor browser MCP with a
  loaded sum-intensity dataset.
- Optional follow-up: merge x-range relayout into `set_series()` when both change in
  the same refresh to avoid a second relayout.
