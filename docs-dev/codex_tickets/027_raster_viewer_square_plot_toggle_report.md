# 027 Raster Viewer Square Plot Toggle Report

## Files changed

- `src/nicewidgets/raster_viewer/frontend/plotly_display_options.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_protocol.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_context_menu.py`
- `src/nicewidgets/raster_viewer/tests/frontend/test_plotly_viewer.py`
- `src/nicewidgets/raster_viewer/tests/frontend/test_plotly_protocol.py`
- `docs/codex_tickets/027_raster_viewer_square_plot_toggle_report.md`

## Summary of implementation

- Added a `square_plot` display option to `PlotlyRasterViewerDisplayOptions`.
- Re-auto-evaluate `square_plot` on every `PlotlyRasterViewer.set_data()` call using pixel shape only: square is enabled when `rows == cols`, and disabled otherwise.
- Added `PlotlyRasterViewer.set_square_plot()` so the context menu can toggle square display for the currently loaded raster.
- Applied square display with Plotly-native layout constraints: `yaxis.scaleanchor = "x"`, `yaxis.scaleratio`, and domain constraints on both axes.
- Removed the unconditional protocol-layer `yaxis.scaleanchor = False`; the viewer display option now owns square/free-stretch behavior.
- Added a right-click context menu item labeled `Square Plot`.

## Tests added or modified

- Added viewer tests for square auto-enable, non-square auto-disable, manual forcing, and re-auto-evaluation after loading new data.
- Updated protocol tests to assert `build_plotly_figure()` leaves square/free-stretch layout ownership to the viewer.

## Exact test commands run

```bash
uv run pytest src/nicewidgets/raster_viewer/tests/frontend/test_plotly_viewer.py src/nicewidgets/raster_viewer/tests/frontend/test_plotly_protocol.py
```

## Test results

- `15 passed in 0.58s`
- Linter check: no linter errors found in touched files.

## Concerns or follow-ups

- Square auto-detection intentionally ignores physical calibration (`dx`/`dy`) per ticket clarification. If future behavior should mean physically square, the auto-rule and `scaleratio` calculation should be revisited together.
