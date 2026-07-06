# 085 Sum Intensity Pool Report

## Files changed

- `src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_core.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_analysis.py`
- `src/acqstore/acq_image/acq_image_list.py`
- `src/acqstore/analysis_pool/sum_intensity_analysis_pool.py`
- `src/cloudscope/events/sum_intensity_pool.py`
- `src/cloudscope/controllers/sum_intensity_pool_controller.py`
- `src/cloudscope/runtime.py`
- `tests/acqstore/test_sum_intensity_analysis_pool.py`
- `tests/cloudscope/test_sum_intensity_pool_controller.py`
- `docs-dev/codex_tickets/085_sum_intensity_pool_report.md`

## Summary of implementation

- Added additive pool-facing APIs on `SumIntensityAnalysis`:
  - `get_pool_summary_columns()`
  - `get_pool_summary_values()`
  - `get_pool_peak_columns()`
  - `get_pool_peak_rows()`
- Kept the existing rich summary/JSON APIs intact. Pool-facing summary output flattens list-like `errors` into scalar `error_count` and `errors_text`.
- Added `LevelCrossing.width_sec` and JSON round-trip support. Core width measurement now stores width in points and seconds.
- Added independent `SumIntensityAnalysisPool` owned by `AcqImageList`.
  - One row per detected peak.
  - One `no_peaks` row when analysis ran and found zero peaks.
  - One `not_analyzed` seed row when no sum-intensity analysis exists for a file/channel/ROI.
  - Uses only the sum-intensity pool-facing API for analysis columns and validates scalar-only cells.
- Attached `sum_intensity_analysis_pool` beside `velocity_analysis_pool` in `AcqImageList`.
- Added `SumIntensityPoolChanged` events and `SumIntensityPoolController`.
- Wired `SumIntensityPoolController` into runtime binding.

## Tests added or modified

- Added `tests/acqstore/test_sum_intensity_analysis_pool.py`.
- Added `tests/cloudscope/test_sum_intensity_pool_controller.py`.

## Exact test commands run

A temporary local `README.md` was created only to satisfy `pyproject.toml` package metadata during `uv` builds because the uploaded source zip did not include root `README.md`. It is not included in the replacement zip.

```bash
uv run pytest tests/acqstore/test_sum_intensity_analysis_pool.py tests/cloudscope/test_sum_intensity_pool_controller.py
uv run pytest tests/acqstore/test_analysis_pool.py tests/acqstore/test_sum_intensity_core.py tests/acqstore/test_sum_intensity_phase2_features.py tests/acqstore/test_sum_intensity_analysis.py tests/cloudscope/test_velocity_pool_controller.py tests/cloudscope/test_sum_intensity_pool_controller.py tests/acqstore/test_sum_intensity_analysis_pool.py
uv run pytest
```

## Test results

- Focused new tests: `16 passed`.
- Focused regression set: `46 passed`.
- Full suite: `1587 passed, 17 skipped, 13 warnings`.

## Concerns or follow-ups

- No `__init__.py` files were modified.
- The pool does not know specific feature names such as `baseline_mean`, `auc`, or `prominence`; those propagate through the sum-intensity pool-facing API.
- No GUI view consumes `SumIntensityPoolChanged` yet. This ticket wires backend and controller state updates only.
