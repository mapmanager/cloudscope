# 122 Randomized Manifest Master Sampling Report

## Files Changed

- `src/acqstore/acq_image/acq_image_manifest.py`
- `src/acqstore/acq_image/acq_image_list.py`
- `scripts/acqstore/try_random_csv.py`
- `tests/acqstore/test_acq_image_list.py`

## Summary Of Implementation

- Changed sampled randomized manifest generation so `to_randomized_manifest_csv(...)` reads from a saved randomized master CSV via `master_csv_path`.
- Removed sampled-manifest reshuffling inputs from the API path: `groupby_column`, `random_seed`, and `root_path`.
- Added validation that sampled manifests are generated only from CSVs with randomized master columns: `_rel_path`, `_group`, `_random_order`, and `_source_index`.
- Updated `scripts/acqstore/try_random_csv.py` to write timestamped master and sampled CSVs into `LOAD_PATH`, with sampled filenames including `_n<N_PER_GROUP>`.
- Updated `scripts/acqstore/try_random_csv.py` to load both the source folder and sampled manifest smoke test lazily with `load_images=False` and `load_analysis_csv=False`.
- Added inline comments describing the script flow.

## Tests Added Or Modified

- Updated `test_randomized_manifest_csv_samples_n_per_group` to assert sampling follows saved master CSV order.
- Updated `test_randomized_manifest_csv_unbalanced_policy` for the new `master_csv_path` API.
- Updated invalid groupby validation to cover master CSV generation.
- Added `test_randomized_manifest_csv_rejects_non_master_csv`.

## Exact Test Commands Run

```bash
uv run pytest tests/acqstore/test_acq_image_list.py
uv run python -m py_compile scripts/acqstore/try_random_csv.py
uv run python -m py_compile scripts/acqstore/try_random_csv.py
```

## Test Results

- `uv run pytest tests/acqstore/test_acq_image_list.py`: 24 passed.
- `uv run python -m py_compile scripts/acqstore/try_random_csv.py`: passed.
- Follow-up `uv run python -m py_compile scripts/acqstore/try_random_csv.py`: passed.
- Edited-file linter check: no linter errors found.

## Concerns Or Follow-Ups

- `to_randomized_manifest_csv(...)` is still exposed on `AcqImageList`, but the new operation primarily samples from `master_csv_path`. This keeps the change small, as requested.
- The sampled CSV intentionally reflects the saved master CSV as the source of truth. If the master CSV is manually edited, sampling will reflect those edits.
