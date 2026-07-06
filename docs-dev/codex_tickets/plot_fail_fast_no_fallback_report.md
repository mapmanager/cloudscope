# Plot Fail-Fast (No Fallback) Report

## Files changed

- `src/nicewidgets/nicepool/plot_errors.py` (new)
- `src/nicewidgets/nicepool/figure_generator.py`
- `src/nicewidgets/nicepool/plot_pool_controller.py`
- `tests/nicewidgets/test_plot_errors.py` (new)
- `tests/nicewidgets/test_plot_pool_controller_errors.py` (new)
- `tests/nicewidgets/test_figure_generator_plot_types.py` (updated)

## Summary of implementation

Removed silent plot-type fallback in `FigureGenerator`. Invalid configuration or insufficient data now raises `PlotConfigurationError` or `PlotDataError` with actionable messages. `PlotPoolController._make_figure_dict` catches these, calls `ui.notify(..., type="warning")`, and returns an annotated empty Plotly figure instead of rendering a different plot type.

Control-panel changes for box/violin/swarm now reuse `require_categorical_group_col()` so notify text matches figure-generation errors.

## Tests added or modified

- `test_plot_errors.py` — helper and exception contracts
- `test_plot_pool_controller_errors.py` — `ui.notify` + empty figure on invalid box config; valid swarm still renders
- `test_figure_generator_plot_types.py` — replaced fallback test with fail-fast tests for box, histogram, grouped

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plot_errors.py tests/nicewidgets/test_plot_pool_controller_errors.py tests/nicewidgets/test_figure_generator_plot_types.py -q
uv run pytest -q
```

## Test results

- Focused: **all passed**
- Full suite: **1366 passed**, 15 warnings

## Concerns or follow-ups

- Embedded `NicePool` in `VelocityPoolView` uses a valid swarm preset; no behavior change expected there.
- `PlotPoolController._replot_current` still has a broad `except Exception` logger path for unexpected failures; configuration/data errors are handled in `_make_figure_dict` before that path.
