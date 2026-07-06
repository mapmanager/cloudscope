# 092 Plotly plot compact bottom margin

## Files changed

- `src/nicewidgets/plotly_plot/widget.py`
- `tests/nicewidgets/test_plotly_plot_widget.py`

## Summary of implementation

Bottom Plotly layout margin (`margin.b`) was stuck at 72 px for all margin presets,
including compact mode when axis labels were hidden. Added
`resolve_plot_layout_margins()` that derives margins from both `show_axis_labels`
and `show_legend` (plus dual-y for right margin):

| Axis labels | Legend | `b` |
|---|---|---|
| off | off | 8 |
| off | on | 40 |
| on | off | 40 |
| on | on | 72 |

Wired the resolver into `build_plotly_figure_dict()`, `_sync_margins_to_plotly_dict()`,
and `set_legend_visible()` (which now syncs margins and relayouts `margin` with legend
changes). Default widget load (labels off, legend on) now uses `b=40` instead of 72.

## Tests added or modified

- Updated `test_build_plotly_figure_dict_includes_config_and_shapes` for default `b=40`
- Added `test_resolve_plot_layout_margins_bottom_by_axis_and_legend`
- Added `test_set_legend_visible_updates_bottom_margin`
- Added `test_axis_labels_toggle_updates_bottom_margin`

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_plot_widget.py -q
```

## Test results

36 passed in 0.68s

## Concerns or follow-ups

- Bottom margin constants (`40` for legend-only / axis-only, `72` for both) were
  chosen to match the prior combined value and raster_viewer order of magnitude; a
  live browser pass on CloudScope analysis plots may warrant fine-tuning if legend
  text wraps or clips at small plot heights.
