# 103 — Home plot stack Pass 1 margins and automargin

## Files changed

- `src/cloudscope/app_config.py`
- `src/nicewidgets/plotly_layout_margins.py` (new)
- `src/nicewidgets/plotly_plot/widget.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_display_options.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
- `src/cloudscope/views/primary_image_view.py`
- `src/cloudscope/views/acq_analysis_plot_view.py`
- `src/cloudscope/views/sum_intensity_plot_view.py`
- `tests/nicewidgets/test_plotly_layout_margins.py` (new)
- `tests/nicewidgets/test_plotly_plot_widget.py`
- `tests/nicewidgets/test_plotly_raster_context_menu.py`
- `tests/cloudscope/test_home_stack_layout_margins.py` (new)

## Summary of implementation

Pass 1 of home-page x-axis visual alignment:

- Added `HOME_STACK_MARGIN_LABELS_ON` / `OFF` and
  `home_stack_layout_margins_profile()` in `app_config.py`.
- Added reusable `PlotlyLayoutMarginsProfile` with optional
  `stabilize_axis_automargin=True` (`automargin=False` on x/y).
- `PlotlyPlotWidget` and `PlotlyRasterViewer` accept an optional margin
  profile; when set, fixed margins replace per-widget margin tables.
- Wired the profile into `PrimaryImageView`, `AcqAnalysisPlotView`, and
  `SumIntensityPlotView`.

Primary raster now uses `r=24` (was `r=10`) when axis labels are on.
Both plot widgets share the same fixed margins and automargin-off behavior,
addressing the observed x=0 horizontal inset difference between acq and
sum-intensity plots.

## Deferred

- X tick ownership (top/middle/bottom roles)
- Shared x tick positions across plots
- Syncing axis-label toggles across the three context menus
- Margin calculator / annotation y-labels

## Tests added or modified

- `tests/nicewidgets/test_plotly_layout_margins.py`
- `tests/cloudscope/test_home_stack_layout_margins.py`
- Profile/automargin tests in plotly plot and raster test files

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_layout_margins.py tests/nicewidgets/test_plotly_plot_widget.py tests/nicewidgets/test_plotly_raster_context_menu.py tests/cloudscope/test_home_stack_layout_margins.py -q
```

## Test results

62 passed in 0.76s

## Concerns or follow-ups

- Browser verification on a real file is still needed to confirm x=0 alignment
  after `automargin=False`.
- Plotly may still choose different x tick **positions** per panel even with
  aligned plot areas; shared tickvals is a Pass 2 item.
- Sum-intensity legend still uses default bottom legend layout with stack `b=40`;
  may be tight when legend is visible.
