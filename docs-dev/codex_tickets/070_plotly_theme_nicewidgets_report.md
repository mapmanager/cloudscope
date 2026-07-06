# Ticket 070: Shared Plotly layout theme (nicewidgets)

## Files changed

### Created
- `src/nicewidgets/plotly_theme.py`
- `tests/nicewidgets/test_plotly_theme.py`
- `docs-dev/codex_tickets/070_plotly_theme_nicewidgets_report.md`

### Deleted
- `src/nicewidgets/raster_viewer/frontend/plotly_theme.py`

### Modified
- `src/nicewidgets/raster_viewer/frontend/plotly_display_options.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
- `src/nicewidgets/nicepool/figure_generator.py`
- `src/nicewidgets/nicepool/plot_pool_controller.py`
- `src/nicewidgets/nicepool/nice_pool.py`
- `src/nicewidgets/nicepool/config.py`

## Summary

Extracted Plotly light/dark layout colors into shared `nicewidgets.plotly_theme` with
`PlotlyTheme`, `PlotlyThemeName`, `PLOTLY_THEMES`, `normalize_plotly_theme()`,
`theme_for_name()`, and `apply_plotly_theme_to_layout()`.

Raster viewer imports the shared module directly (old raster-specific file deleted).
Pool `FigureGenerator` applies layout theme at the end of `make_figure()`.
`PlotPoolController` / `NicePool` expose `set_dark_mode()` / `set_theme()` and
refresh all visible plots via `_refresh_all_plot_figures()` on theme change.

v1 scope is layout/axis colors only; scatter/swarm markers and selection overlay
colors are unchanged.

## Tests added or modified

- `tests/nicewidgets/test_plotly_theme.py` — shared helpers, figure generator, controller

## Test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_theme.py tests/nicewidgets/test_plotly_raster_context_menu.py
uv run pytest
```

## Test results

```
35 passed (focused)
1173 passed, 2 skipped, 13 warnings (full suite)
```

## Concerns or follow-ups

- Trace/mean/selection colors remain theme-independent (future ticket if desired).
- Pool theme is not persisted in `PoolPlotConfig`.
