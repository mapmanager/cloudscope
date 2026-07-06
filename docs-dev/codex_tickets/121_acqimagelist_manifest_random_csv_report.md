# 121 AcqImageList Manifest Random CSV Report

## Files changed

- `src/acqstore/acq_image/acq_image_list.py`
- `src/acqstore/acq_image/acq_image_manifest.py`
- `tests/acqstore/test_acq_image_list.py`
- `scripts/acqstore/try_random_csv.py`
- `docs-dev/codex_tickets/121_acqimagelist_manifest_random_csv_report.md`

## Summary of implementation

- Switched AcqImageList CSV manifest loading to require `_rel_path` with no `rel_path` backward compatibility.
- Added structured load warning fields and `LoadErrorType` categories for missing files, unsupported file types, loader errors, and CSV errors.
- Added `source_root_path` tracking for file, folder, and manifest CSV load paths.
- Added `AcqImageList.from_manifest_csv()` as a safe manifest loader returning `LoadResult`.
- Added thin `AcqImageList` manifest-writing wrappers:
  - `to_manifest_csv()`
  - `to_randomized_manifest_master_csv()`
  - `to_randomized_manifest_csv()`
- Added `acq_image_manifest.py` to compartmentalize manifest writing, grouping validation, deterministic shuffling, and sampled CSV generation.
- Added per-file `logger.error(...)` calls for missing manifest targets and loader failures.
- Confirmed existing CloudScope GUI CSV load path already routes `.csv` loads through the backend `PathKind.CSV` path; no GUI files were changed.
- Added a development script, `scripts/acqstore/try_random_csv.py`, with hard-coded variables for exercising folder load, manifest writing, randomized master writing, sampled writing, and sampled reload.

## Tests added or modified

Updated existing AcqImageList CSV tests from `rel_path` to `_rel_path` and added coverage for:

- duplicate `_rel_path` warnings
- absolute `_rel_path` rejection
- `_rel_path` escaping manifest root rejection
- missing manifest file structured warnings
- loader exception structured warnings
- `source_root_path` for folder, file, and CSV loads
- `to_manifest_csv()` output
- deterministic randomized master CSV generation
- sampled randomized CSV generation
- unbalanced group policy
- invalid group column and invalid group type validation

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_acq_image_list.py
uv run pytest tests/acqstore/test_acq_image_list.py tests/acqstore/test_acq_image_list_progress_cancel.py
uv run pytest
```

## Test results

```text
tests/acqstore/test_acq_image_list.py: 23 passed
tests/acqstore/test_acq_image_list.py tests/acqstore/test_acq_image_list_progress_cancel.py: 25 passed
full suite: 1732 passed, 17 skipped, 13 warnings
```

The skipped tests were due to missing optional fixtures or optional matplotlib availability in the sandbox environment. The warnings were existing pytest/deprecation/runtime warnings unrelated to this ticket.

## Concerns or follow-ups

- CloudScope GUI currently reports warning counts and logs detailed failures, which is sufficient for this ticket. A later GUI ticket can expose the structured warning fields in a detailed load report dialog/table.
- The manifest randomization API uses current `ACQ_FILE_LIST_SCHEMA` rows. If future grouping should support additional experimental metadata fields beyond the file-list schema, that should be a separate schema/API expansion ticket.
- `scripts/acqstore/try_random_csv.py` intentionally uses hard-coded local paths and may require editing before running on another machine.
