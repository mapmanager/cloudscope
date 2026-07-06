# 083 Sum Intensity Plot View Report

## Files changed

- `src/cloudscope/views/sum_intensity_plot_view.py`
- `src/cloudscope/views/view_ids.py`
- `src/cloudscope/pages/home_page.py`
- `tests/cloudscope/test_sum_intensity_plot_view.py`
- `docs-dev/codex_tickets/083_sum_intensity_plot_view_report.md`

## Summary of implementation

Added a first-class CloudScope `SumIntensityPlotView` that owns a reusable `PlotlyPlotWidget` child and renders already-computed single-file/channel/ROI sum-intensity analysis results. The view consumes only public AcqStore `SumIntensityAnalysis` result APIs: continuous traces, event points, width traces, and summary values.

The view listens for matching `AnalysisCompleted`, `RoiChanged`, and `PrimaryXRangeChanged` events. User Plotly x-range changes are translated into `SetPrimaryXRangeIntent`. Measurement callbacks are wired and stored locally for a later ticket that will translate draggable line edits into sum-intensity detection-parameter intents.

The home page now instantiates, builds, and registers the sum-intensity plot view in the analysis pane below the existing primary analysis plot.

## Tests added or modified

- Added `tests/cloudscope/test_sum_intensity_plot_view.py`.

## Exact test commands run

The uploaded source zip does not include repo root `README.md`, but `uv build` requires it. For local test execution only, an empty temporary `README.md` was created in the sandbox checkout. It is not included in this replacement zip.

```bash
uv run pytest tests/cloudscope/test_sum_intensity_plot_view.py tests/cloudscope/test_acq_analysis_plot_view.py tests/cloudscope/test_x_range_view_wiring.py -q
```

```bash
uv run pytest tests/cloudscope/test_home_page_build.py tests/cloudscope/test_left_toolbar_view.py -q
```

## Test results

- `52 passed`
- `3 passed`

## Concerns or follow-ups

- Ticket 083 intentionally does not mutate sum-intensity detection parameters from draggable measurement lines. A follow-up ticket should add the intent/state path for plot measurement callbacks.
- Ticket 083 intentionally does not refactor the left-toolbar sum-intensity parameter view to use schema `visible`, `description`, or `category` metadata. That should remain a separate focused ticket.
- The plot view currently shares the analysis pane with the existing primary analysis plot. If the final UX should make these mutually exclusive or tabbed, that should be handled by a separate layout ticket.
