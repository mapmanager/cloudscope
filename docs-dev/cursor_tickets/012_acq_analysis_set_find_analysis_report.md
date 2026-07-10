# 012 — AcqAnalysisSet find_analysis report

## Summary of implementation

Added `AcqAnalysisSet.find_analysis()` as a nullable scripting convenience over
`get()` that mirrors the existing `get_analysis()` signature (`str |
type[BaseAnalysis]`, keyword-only `channel` and `roi_id`). Returns `None` when no
matching analysis exists; raises `TypeError` for invalid selector types. Updated
`get_analysis()` docstring with a cross-reference to `find_analysis()`.

## Files changed

- `src/acqstore/acq_image/acq_analysis_set.py`
- `tests/acqstore/test_acq_analysis_set.py`
- `docs-dev/cursor_tickets/012_acq_analysis_set_find_analysis_report.md`

## Tests added or modified

Added:

- `test_find_analysis_resolves_by_class`
- `test_find_analysis_resolves_by_name_string`
- `test_find_analysis_missing_returns_none`
- `test_find_analysis_rejects_invalid_type`

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_acq_analysis_set.py -k find_analysis -v
uv run pytest tests/acqstore/test_acq_analysis_set.py -v
```

## Test results

All passed:

- `tests/acqstore/test_acq_analysis_set.py -k find_analysis`: 4 passed
- `tests/acqstore/test_acq_analysis_set.py`: 23 passed

## Concerns or follow-ups

- Batch pool and other call sites that use `analysis_set.get(AnalysisKey(...))`
  can adopt `find_analysis()` when convenient; no refactor required for this
  ticket.
- Unregistered analysis name strings return `None` (lookup semantics), consistent
  with `get(key)`.
