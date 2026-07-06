# Ticket 010 — AcqAnalysisPlotView extended tests

## Files changed

- `tests/cloudscope/test_acq_analysis_plot_view.py` — extended from 5 to 27 tests
- `docs/codex_tickets/010_acq_analysis_plot_view_tests_report.md` (this report)

## Summary of implementation

Added 22 tests covering the analysis-plot view branches that were previously
uncovered. A `_FakeChart` (with embedded `_FakeEvents`) and `_FakeLabel` let
the headless tests assert on `set_line_data`, `clear`, `events.set_events`,
`events.select_event`, `events.set_visible`, `begin_select_x_range`,
`cancel_select_x_range`, and x-axis limits, all without instantiating an
EChartWidget.

Also extended `FakeAnalysisSet` with a `get()` method so refresh-plot tests
exercise the (now-present) `_get_selected_event_overlays` look-up.

New tests cover:

- `_refresh_plot`: clears chart + status text when no plot data; pushes
  line data + status text when data is present; no-op without chart.
- `_empty_message`: file/channel/ROI missing branches plus "no
  primary-kymograph analysis" branch.
- `set_x_axis_limits` / `reset_x_axis_limits`: forward to chart and are
  no-ops when no chart is set.
- `_on_begin_plot_x_range_selection`: starts chart x-range mode when the
  selection matches; ignored for mismatches; safe without a chart.
- `_on_cancel_plot_x_range_selection`: always calls chart cancel; safe
  without a chart.
- `_on_acq_image_events_changed`: pushes overlay events, selection, and
  visibility when matching; ignored for other selections; safe without a
  chart.
- `_on_acq_image_event_selection_changed`: forwards string ids; falls
  back to clearing selection on `KeyError`; safe without a chart.
- `_on_x_range_selected`: publishes `AcqImageEventXRangeSelectedIntent`
  using the current selection.
- `_overlay_rows_to_objects` / `_OverlayRowObject`: translate row fields;
  default `event_type` to `"user"`.

## Tests added or modified

22 new tests in `tests/cloudscope/test_acq_analysis_plot_view.py`.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_acq_analysis_plot_view.py -q
uv run pytest tests/cloudscope/test_acq_analysis_plot_view.py --cov=cloudscope.views.acq_analysis_plot_view --cov-report=term-missing -q
```

## Test results

- 27 passed
- `acq_analysis_plot_view.py` coverage: **49% → 80%** (160 statements, 32 missed)
- Remaining missed lines are `build()` and `_build_content` (73-81, 89-94,
  145-148), several lifecycle log lines, and the `_get_selected_event_overlays`
  EventAnalysis-typed branch (requires a real EventAnalysis to satisfy
  `isinstance`).

## Concerns or follow-ups

- The `_get_selected_event_overlays` EventAnalysis branch could be covered by
  reusing the real `EventAnalysis` class from `acqstore` in a follow-up
  ticket.

## Follow-up on 2026-05-26

Updated `tests/cloudscope/test_acq_analysis_plot_view.py` after the status-label
updates in `src/cloudscope/views/acq_analysis_plot_view.py` were intentionally
commented out. The source file was left untouched.

Changes:

- `test_refresh_plot_clears_chart_and_sets_status_when_no_plot_data` was renamed
  to `test_refresh_plot_clears_chart_when_no_plot_data`.
- The no-plot-data test now asserts the chart clears and the status label keeps
  its previous text.
- The available-plot-data test now asserts line data is pushed and the status
  label remains unchanged.

Exact test commands run:

```bash
uv run pytest tests/cloudscope/test_acq_analysis_plot_view.py -q
uv run pytest -q
```

Test results:

- `tests/cloudscope/test_acq_analysis_plot_view.py`: 27 passed
- Full suite: 739 passed, 3 warnings
