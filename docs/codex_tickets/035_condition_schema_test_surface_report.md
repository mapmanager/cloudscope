# 035 Condition Schema Test Surface Report

## Files changed

- `tests/acqstore/test_acq_image_list.py`
- `tests/acqstore/test_acq_image_tree_rows.py`
- `docs/codex_tickets/035_condition_schema_test_surface_report.md`

## Summary of implementation

- Confirmed production `AcqImage.get_schema_row()` already emits `condition` from `ExperimentMetadata`.
- Confirmed `ExperimentMetadata` defines `condition` and coerces it through `from_dict`.
- Confirmed analysis tree rows derive their schema keys from `ACQ_FILE_LIST_SCHEMA`, so the new field is included automatically for analysis child rows.
- Updated stale test fakes to include the new `condition` schema field.
- Added focused assertions that `condition` is present on schema rows/tree file rows.

## Tests added or modified

- Updated `_FakeAcqImage.get_schema_row()` in `tests/acqstore/test_acq_image_list.py`.
- Updated `_FakeMetadata` in `tests/acqstore/test_acq_image_tree_rows.py`.
- Added assertions covering the `condition` value in both files.

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_acq_image_list.py tests/acqstore/test_acq_image_tree_rows.py
```

## Test results

- `19 passed in 0.58s`
- `ReadLints` found no linter errors in edited test files.

## Concerns or follow-ups

- None. The failures were caused by test doubles that no longer matched the backend schema surface.
