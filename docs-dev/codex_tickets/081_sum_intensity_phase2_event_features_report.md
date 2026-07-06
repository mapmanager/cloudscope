# 081 Sum Intensity Phase 2 Event Features Report

## Files changed

- `src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_core.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_analysis.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_features.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_presets.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/README.md`
- `docs-dev/acqstore/analysis/sum_intensity_architecture.md`
- `tests/acqstore/test_sum_intensity_core.py`
- `tests/acqstore/test_sum_intensity_analysis.py`
- `tests/acqstore/test_sum_intensity_phase2_features.py`
- `tests/acqstore/acq_image/analysis/sum_intensity_analysis/test_sum_intensity_schema_metadata.py`
- `tests/acqstore/acq_image/analysis/sum_intensity_analysis/test_sum_intensity_synthetic.py`

## Summary of implementation

Added phase-2 event-level feature extraction for sum-intensity analysis. The new
features extend the existing `PeakEvent` construction path and do not create a
parallel feature pipeline.

New event features:

- `baseline_mean`
- `baseline_std`
- `rise_10_90_sec`
- `decay_90_10_sec`
- `decay_time_sec`
- `max_rise_slope`
- `max_decay_slope`
- `auc`
- `prominence`

Each feature is stored as an `EventFeature` with `value`, `status`, and `reason`
so expected scientific failures are serialized as data rather than raised as
runtime exceptions.

Added `baseline_window_ms` as a visible preprocessing detection parameter. This
parameter controls the pre-onset baseline window used for `baseline_mean`,
`baseline_std`, and `prominence`.

Added `sum_intensity_features.py` with `SumIntensityFeatureSchema`, feature
categories, and public schema accessors. `SumIntensityAnalysis` now exposes:

- `get_feature_schema()`
- `get_feature_schema_dataframe()`

Updated package and architecture documentation to describe the new feature schema
and feature algorithms.

## Tests added or modified

Added:

- `tests/acqstore/test_sum_intensity_phase2_features.py`

Modified existing focused sum-intensity tests to include `baseline_window_ms` in
complete detection parameter dictionaries and to validate schema metadata.

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_sum_intensity_phase2_features.py -q
uv run pytest tests/acqstore/test_sum_intensity_core.py tests/acqstore/test_sum_intensity_analysis.py tests/acqstore/test_sum_intensity_phase2_features.py -q
uv run pytest tests/acqstore/test_sum_intensity_core.py tests/acqstore/test_sum_intensity_analysis.py tests/acqstore/test_sum_intensity_phase2_features.py tests/acqstore/acq_image/analysis/sum_intensity_analysis -q
uv run pytest tests/acqstore/test_analysis_detection_schema.py tests/acqstore/test_sum_intensity_core.py tests/acqstore/test_sum_intensity_analysis.py tests/acqstore/test_sum_intensity_phase2_features.py tests/acqstore/acq_image/analysis/sum_intensity_analysis -q
```

## Test results

- `tests/acqstore/test_sum_intensity_phase2_features.py`: 3 passed
- focused sum-intensity core/wrapper/phase2 tests: 13 passed
- focused sum-intensity package tests: 27 passed
- focused detection-schema plus sum-intensity suite: 38 passed

## Concerns or follow-ups

- `auc` is currently defined as AUC from left 10% crossing to right 10% crossing
  above onset value. Future work may add additional AUC variants such as
  `auc_20` or an event-off detector.
- `decay_time_sec` is currently an alias of `decay_90_10_sec`.
- Exponential rise/decay fits are intentionally not included in this ticket.
- Future event-pool work should flatten `EventFeature.value`, `EventFeature.status`,
  and `EventFeature.reason` explicitly rather than parsing JSON ad hoc.
