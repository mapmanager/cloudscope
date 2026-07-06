# 080 PlotlyPlotWidget Foundation Report

## Files changed

- `src/nicewidgets/plotly_plot/__init__.py`
- `src/nicewidgets/plotly_plot/models.py`
- `src/nicewidgets/plotly_plot/widget.py`
- `tests/nicewidgets/test_plotly_plot_widget.py`
- `scripts/nicewidgets/try_plotly_plot_widget.py`

## Summary of implementation

Added a standalone `nicewidgets.plotly_plot` package with a reusable `PlotlyPlotWidget` for NiceGUI. The package `__init__.py` is intentionally empty; callers import public classes from explicit module paths such as `nicewidgets.plotly_plot.widget` and `nicewidgets.plotly_plot.models`. The widget is independent of CloudScope and exposes public APIs for:

- adding, updating, removing, and clearing named continuous `scattergl` traces
- adding, updating, removing, and clearing named sparse scatter overlays
- setting and resetting x-axis limits programmatically
- reporting user-driven x-axis range changes through an init callback
- adding/removing draggable horizontal or vertical measurement lines
- adding/removing draggable horizontal or vertical measurement pairs with delta reporting

The widget stores a local Plotly figure dictionary and pushes incremental browser updates with Plotly JavaScript primitives (`addTraces`, `restyle`, `deleteTraces`, and `relayout`) rather than calling full NiceGUI `update()` after startup.

The initial Plotly configuration is passed through the root figure dictionary using `config.editable = True` and `config.scrollZoom = True`, matching NiceGUI's declarative Plotly API.

## Tests added or modified

Added `tests/nicewidgets/test_plotly_plot_widget.py` covering:

- trace and scatter data validation
- axis range validation, including partial-bound rejection
- figure dictionary construction
- named trace add/update/remove behavior
- named scatter add/update/remove behavior
- programmatic x-axis limit behavior
- user x-range callback parsing
- single measurement line drag callback behavior
- measurement pair drag callback and delta behavior

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_plot_widget.py -q
```

## Test results

```text
10 passed in 1.93s
```

## Concerns or follow-ups

- This ticket intentionally does not modify CloudScope MVC, controller events, or views.
- Browser drag behavior is exercised by `scripts/nicewidgets/try_plotly_plot_widget.py`; unit tests validate the Python state and callback parsing but cannot fully simulate Plotly browser drag mechanics.
- The demo script uses explicit module imports because `src/nicewidgets/plotly_plot/__init__.py` is intentionally empty by project convention.
- Future CloudScope integration should route measurement callbacks through CloudScope intents/state rather than directly mutating detection parameters from the plot view.
- The uploaded source zip did not contain the root `README.md` referenced by `pyproject.toml`; a temporary sandbox-only README was created so `uv run pytest` could build the editable package. That temporary README is not part of this replacement ticket.
