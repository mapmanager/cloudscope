# Analysis pool conditional column prefix

## Files changed

- `src/acqstore/analysis_pool/base_analysis_pool.py`
- `src/acqstore/analysis_pool/velocity_analysis_pool.py`
- `src/acqstore/acq_image/analysis/model.py`
- `src/cloudscope/views/velocity_pool_view.py`
- `tests/acqstore/test_analysis_pool.py`
- `tests/cloudscope/test_velocity_pool_view.py`
- `tests/nicewidgets/test_plot_summary.py`
- `tests/nicewidgets/test_selection_handler.py`
- `tests/nicewidgets/test_figure_generator_selection.py`
- `tests/nicewidgets/test_nicepool.py`

## Summary of implementation

Analysis pool column names no longer blindly prepend `velocity_`, `hr_`, or `event_` to every summary key. New helper `pool_column_name()` leaves keys that already start with `{prefix}_` unchanged (for example `velocity_mean` stays `velocity_mean`) and prefixes shared metadata keys such as `analysis_date` (for example `velocity_analysis_date`).

Column specs are cached once per concrete pool class via `get_analysis_column_specs()` and exposed through `pool_column_names()` so schema construction and row building share one source of truth. CloudScope's empty velocity-pool fallback DataFrame now calls `VelocityAnalysisPool.pool_column_names()` instead of duplicating prefix logic.

Default velocity-pool plot Y column updated from `velocity_velocity_mean` to `velocity_mean`.

Heart-rate pool refresh on analysis completion remains out of scope (separate follow-up). Scripts using the acqstore API should call `velocity_analysis_pool.refresh_row(...)` or `rebuild()` after mutating heart-rate analyses so pool columns reflect current summaries.

## Tests added or modified

- Added `test_pool_column_name_skips_existing_prefix`
- Added `test_velocity_analysis_pool_column_names_are_unique`
- Updated analysis-pool integration tests for new column names
- Updated velocity-pool view and nicewidgets tests using old `velocity_velocity_mean` column

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_analysis_pool.py tests/cloudscope/test_velocity_pool_view.py tests/nicewidgets/test_plot_summary.py tests/nicewidgets/test_selection_handler.py tests/nicewidgets/test_figure_generator_selection.py tests/nicewidgets/test_nicepool.py -q
uv run pytest -q
```

## Test results

- Focused tests: 36 passed
- Full suite: 1293 passed

## Concerns or follow-ups

- Heart-rate analysis completion does not trigger `VelocityPoolController` row refresh; scripts must call `refresh_row` or `rebuild` explicitly until a follow-up wires HR completion events.
- Exported CSV column headers change (`velocity_mean` replaces `velocity_velocity_mean`); external consumers of pool CSV exports may need updating.
