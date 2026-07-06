# 086 Analysis Pool Tabs Report

## Files changed

- `src/acqstore/analysis_pool/sum_intensity_analysis_pool.py`
- `src/nicewidgets/nicepool/selection_handler.py`
- `src/nicewidgets/nicepool/plot_pool_controller.py`
- `src/nicewidgets/nicepool/nice_pool.py`
- `src/cloudscope/views/velocity_pool_view.py`
- `src/cloudscope/views/sum_intensity_pool_plot_config.py`
- `tests/acqstore/test_sum_intensity_analysis_pool.py`
- `tests/cloudscope/test_velocity_pool_view.py`
- `tests/nicewidgets/test_plot_pool_controller.py`
- `docs-dev/codex_tickets/086_analysis_pool_tabs_report.md`

## Summary of implementation

- Extended `VelocityPoolView` (right-panel analysis pools) with NiceGUI tabs:
  **Velocity** and **Peaks**, each hosting its own `NicePool`.
- Velocity tab unchanged in behavior: `velocity_analysis_pool` DataFrame,
  `VelocityPoolChanged` refresh, single-row primary-selection highlight.
- Peaks tab: `sum_intensity_analysis_pool` DataFrame, `SumIntensityPoolChanged`
  refresh, default plot preset in `sum_intensity_pool_plot_config.py`
  (`peak_row_type=peak`, `peak_amplitude` y-axis).
- While the right panel is visible, both pools refresh on either pool-changed
  event; row click still emits `SelectFileIntent(file_id, channel, roi_id)` only.
- Added `SumIntensityAnalysisPool.row_ids_for_selection()` for peak-row lookup.
- Added `NicePool.select_points_by_row_ids()` so the Peaks tab can highlight all
  peak rows for the current primary selection (no highlight for `no_peaks` /
  `not_analyzed` sentinel rows).
- Kept `ViewId.VELOCITY_POOL` and class/file name unchanged (rename deferred).

## Tests added or modified

- Extended `tests/cloudscope/test_velocity_pool_view.py` for dual-tab build,
  plot configs, dual refresh, theme sync, velocity and peaks selection sync.
- Added `row_ids_for_selection` tests in
  `tests/acqstore/test_sum_intensity_analysis_pool.py`.
- Added `select_points_by_row_ids` delegation test in
  `tests/nicewidgets/test_plot_pool_controller.py`.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_velocity_pool_view.py tests/acqstore/test_sum_intensity_analysis_pool.py tests/nicewidgets/test_plot_pool_controller.py
uv run pytest
```

## Test results

- Focused tests: `34 passed`.
- Full suite: `1610 passed, 15 warnings`.

## Concerns or follow-ups

- Per-tab lazy build and per-tab event detach (mirroring left toolbar) deferred
  to a future ticket; both NicePools are built when the panel first opens.
- `pool_page.py` unchanged (deprecated standalone route).
- Future: rename `VelocityPoolView` / `ViewId.VELOCITY_POOL`; pass `peak_id`
  through pool row selection for `SumIntensityPlotView` sync.
