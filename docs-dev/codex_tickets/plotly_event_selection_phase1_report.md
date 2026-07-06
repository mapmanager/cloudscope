# Plotly event selection — Phase 1 report

## Files changed

- `src/nicewidgets/plotly_plot/widget.py`
- `scripts/nicewidgets/try_plotly_plot_event_overlays.py` (new)
- `tests/nicewidgets/test_plotly_plot_widget.py`
- `docs-dev/codex_tickets/plotly_event_selection_phase1_report.md`

## Summary

Phase 1 of the EChart → `PlotlyPlotWidget` swap: relayout logging, box-select
x-range mode (kymflow-inspired patterns), self-relayout echo suppression,
raster-inspired bracket axis filter, double-click reset, and an independent try
script for manual GUI validation.

Not in this phase: `plot.events` overlay API, `AcqAnalysisPlotView` swap.

## Tests added or modified

- `test_extract_rect_selection_parses_flat_keys`
- `test_extract_rect_selection_parses_list_form`
- `test_begin_select_x_range_echo_does_not_emit_x_range_changed`
- `test_box_select_emits_on_x_range_selected_once`
- `test_doubleclick_resets_x_range_and_emits_auto`

## Test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_plot_widget.py -q
uv run pytest tests/nicewidgets/test_plotly_plot_widget.py tests/cloudscope/test_acq_analysis_plot_view.py tests/cloudscope/test_x_range_view_wiring.py -q
```

## Test results

64 passed (plotly + related cloudscope wiring tests).

## Manual try script

```bash
uv run python scripts/nicewidgets/try_plotly_plot_event_overlays.py
```

Watch terminal INFO logs for every `plotly_relayout` payload while arming
box-select, zooming, and double-clicking.

## Concerns / follow-ups

- Event overlay shapes (`plot.events`) — Phase 2.
- `AcqAnalysisPlotView` widget swap — Phase 3 after try-script gate passes.
- Relayout behavior is still empirical; iterate using logged payloads from the
  try script and real CloudScope GUI sessions.
