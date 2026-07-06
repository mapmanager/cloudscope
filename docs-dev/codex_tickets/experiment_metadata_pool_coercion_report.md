# Experiment metadata coercion for velocity pool

## Files changed

- `src/acqstore/acq_image/metadata.py`
- `src/acqstore/analysis_pool/base_analysis_pool.py`
- `tests/acqstore/test_metadata.py`
- `tests/acqstore/test_analysis_pool.py`

## Summary of implementation

- Unified schema-driven coercion in `ExperimentMetadata._coerce_schema_value`, used by
  `from_dict`, `update_values`, and `_coerce_patch_value`.
- Sidecar JSON strings such as `"depth": "75"` and `"branch_order": "2"` now coerce to
  `float`/`int`; empty strings coerce to `None`.
- Invalid numeric strings fail fast with `ValueError` naming the field (option A).
- Velocity pool applies nullable pandas dtypes (`Int64`, `Float64`) to experiment-metadata
  numeric columns on `rebuild()` and `refresh_row()`.

## Tests added or modified

- Added: `test_experiment_metadata_from_dict_coerces_string_numbers`
- Added: `test_experiment_metadata_from_dict_coerces_empty_string_to_none_for_numeric`
- Added: `test_experiment_metadata_from_dict_rejects_invalid_depth`
- Added: `test_experiment_metadata_from_dict_rejects_non_integer_branch_order`
- Added: `test_velocity_analysis_pool_coerces_stringly_experiment_metadata_dtypes`

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_metadata.py tests/acqstore/test_analysis_pool.py tests/nicewidgets/test_plot_categorical_errors.py -q
uv run pytest -q
```

## Test results

- Focused: **30 passed**
- Full suite: run at commit time

## Concerns or follow-ups

- Sidecar load now raises on invalid numeric metadata; one bad JSON file blocks loading
  that file's sidecar state (intentional fail-fast).
- Re-run typed sync script on folders that still contain legacy string sidecars if files
  were never updated (`DRY_RUN=True` in dev script leaves JSON unchanged).
