# 082 Sum Intensity Schema Categories Report

## Files changed

- `src/acqstore/acq_image/analysis/model.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_analysis.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/README.md`
- `docs-dev/acqstore/analysis/sum_intensity_architecture.md`
- `tests/acqstore/test_analysis_detection_schema.py`
- `tests/acqstore/acq_image/analysis/sum_intensity_analysis/test_sum_intensity_schema_metadata.py`

## Summary of implementation

Added backend-owned detection parameter presentation metadata. `DetectionParamSchema`
now supports an optional `category` field using the new `DetectionParamCategory`
enum. Sum-intensity parameters are grouped as `Preprocessing` or `Peak Detection`.
Advanced fields `baseline_min_value` and `level_fractions` remain in the schema
and default params but are hidden by default with `visible=False`.

## Tests added or modified

- Added focused sum-intensity schema metadata tests.
- Updated the generic detection schema DataFrame test to expect the new category column.

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_analysis_detection_schema.py tests/acqstore/acq_image/analysis/sum_intensity_analysis/test_sum_intensity_schema_metadata.py -q
uv run pytest tests/acqstore/acq_image/analysis/sum_intensity_analysis -q
```

## Test results

- `tests/acqstore/test_analysis_detection_schema.py tests/acqstore/acq_image/analysis/sum_intensity_analysis/test_sum_intensity_schema_metadata.py`: passed.
- `tests/acqstore/acq_image/analysis/sum_intensity_analysis`: passed.

## Concerns or follow-ups

No GUI code was changed. Future CloudScope views can use `field.category` and
`field.visible` to render section headings and hide advanced fields while keeping
backend validation unchanged.
