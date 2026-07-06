# Raster viewer traces default and axis-label margins

## Files changed

- `src/cloudscope/views/primary_image_view.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_protocol.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
- `tests/cloudscope/test_theme_event.py`
- `tests/nicewidgets/test_plotly_raster_context_menu.py`
- `docs-dev/codex_tickets/raster_viewer_traces_and_margins_report.md`

## Summary of implementation

- Primary image view now passes `show_trace_overlays=False` in
  `PlotlyRasterViewerDisplayOptions`, so diameter/analysis traces stay hidden
  until the user enables **Traces** in the context menu. Reference image view
  is unchanged (traces on by default for scan path).
- Added `PLOTLY_MARGIN_WITH_AXIS_LABELS` and `PLOTLY_MARGIN_COMPACT` in
  `plotly_protocol.py`.
- `PlotlyRasterViewer` syncs layout margins from `show_axis_labels`:
  compact `{8,8,8,8}` when labels hidden; labeled `{l:40, r:10, t:10, b:40}`
  when shown. Margins update on init, `set_data`, and context-menu toggle.

## Tests added or modified

- `tests/cloudscope/test_theme_event.py`
  - `test_primary_image_view_hides_trace_overlays_by_default`
- `tests/nicewidgets/test_plotly_raster_context_menu.py`
  - margin assertions in `test_axis_labels_are_hidden_by_default_but_preserved_for_toggle`
  - margin assertion in `test_viewer_accepts_caller_supplied_display_options`
  - `test_axis_label_margin_toggle_swaps_between_compact_and_labeled`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_theme_event.py tests/nicewidgets/test_plotly_raster_context_menu.py -q
```

## Test results

```
uv run pytest tests/cloudscope/test_theme_event.py tests/nicewidgets/test_plotly_raster_context_menu.py -q
.....................                                                    [100%]
21 passed in 1.46s
```

## Concerns or follow-ups

- Compact margin values (`8px` symmetric) may need tuning after visual QA.
- Reference scan-path legend spacing with compact margins deferred unless QA
  reports clipping.
