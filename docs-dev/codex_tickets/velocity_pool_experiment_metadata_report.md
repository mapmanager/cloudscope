# Velocity pool experiment metadata columns

## Files changed

- `src/acqstore/acq_image/metadata.py`
- `src/acqstore/analysis_pool/base_analysis_pool.py`
- `src/cloudscope/controllers/velocity_pool_controller.py`
- `tests/acqstore/test_metadata.py`
- `tests/acqstore/test_analysis_pool.py`
- `tests/cloudscope/test_velocity_pool_controller.py`
- `docs/schemas/experimental_metadata.md` (regenerated)

## Summary of implementation

- Added `age` (`str`) to `EXPERIMENT_METADATA_SCHEMA` and `ExperimentMetadata` in the Animal group.
- Extended velocity pool `base_columns` with experiment-metadata fields: `age`, `sex`, `branch_order`, `direction`, `depth`, `note` (`genotype` was already present).
- Populated the new columns in `AnalysisPool._build_base_row` from `ExperimentMetadata.get_values()` via the public `get_metadata_section` API.
- Subscribed `VelocityPoolController` to `MetadataChanged` so experiment-metadata edits refresh all pool rows for the affected file.

## Tests added or modified

- Added: `test_experiment_metadata_age_defaults_to_empty_string` in `tests/acqstore/test_metadata.py`
- Modified: `tests/acqstore/test_analysis_pool.py` (fake acq image experiment metadata + column assertions)
- Added: `test_experiment_metadata_changed_on_empty_pool_is_noop`
- Added: `test_experiment_metadata_changed_refreshes_matching_pool_rows`
- Added: `test_image_header_metadata_changed_does_not_refresh_pool`
- Modified: `FakeVelocityPool` in `tests/cloudscope/test_velocity_pool_controller.py` (supports `get_dataframe`)

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_metadata.py tests/acqstore/test_analysis_pool.py tests/cloudscope/test_velocity_pool_controller.py -q
uv run python scripts/docs/generate_schema.py
uv run pytest -q
```

## Test results

- Focused tests: **30 passed**
- Full suite: **1427 passed, 5 failed**
- Pre-existing failures (unrelated to this ticket): `tests/acqstore/test_acq_image_tree_rows.py` (5 tests) — `_FakeImages` missing `has_reference_image` attribute in `get_schema_row()`.

## Concerns or follow-ups

- New experiment-metadata columns appear in the velocity pool only; `ACQ_FILE_LIST_SCHEMA` / file-list table unchanged by design.
- Old sidecars without `age` load with default empty string; no migration required.
