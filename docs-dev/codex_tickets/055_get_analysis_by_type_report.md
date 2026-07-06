# 055 — Type-based analysis getter (`get_analysis`)

## Summary

Added an explicit, public getter on `AcqAnalysisSet` so scripting users (and the
docs notebooks) can retrieve an analysis by **type, channel, and ROI** without
holding onto a previously created analysis instance just to reuse its `.key`.

Previously the notebooks did:

```python
loaded = reloaded.analysis_set.get_required(velocity.key)
```

which couples the "reload from disk" cell to the in-memory `velocity` object from
an earlier "run" cell. Now they do:

```python
loaded_analysis = reloaded.analysis_set.get_analysis(
    RadonVelocityAnalysis, channel=CHANNEL, roi_id=ROI_ID
)
```

### Design decisions (confirmed with user)

- Added a single **required** getter `get_analysis(...)` that raises `KeyError`
  when missing (matches the notebook reload use case). No optional variant was
  added.
- `get_analysis` accepts `str | type[BaseAnalysis]`, consistent with
  `create_and_run`.
- The `str | class -> analysis_name` resolution that was inlined in
  `create_and_run` was extracted into a shared private static helper
  `_resolve_analysis_name`, now used by both methods (justified by two callers).
- The existing key-based `get` / `get_required` pair was kept as-is. They are the
  standard optional/required pair (like `dict.get` vs `dict[]`), not redundant;
  `get_analysis` delegates to `get_required`.

## Files changed

- `src/acqstore/acq_image/acq_analysis_set.py`
  - Added `_resolve_analysis_name(analysis)` static helper.
  - Refactored `create_and_run` to use it (removed duplicated type-check block).
  - Added public `get_analysis(analysis, *, channel, roi_id) -> BaseAnalysis`.
- `docs/notebooks/velocity-analysis.ipynb`
  - Save/load cell now uses `get_analysis(RadonVelocityAnalysis, ...)` and renames
    `loaded` -> `loaded_analysis`.
- `docs/notebooks/diameter-analysis.ipynb`
  - Save/load cell now uses `get_analysis(DiameterAnalysis, ...)` and renames
    `loaded` -> `loaded_analysis`.
- `tests/acqstore/test_acq_analysis_set.py`
  - Added tests for `get_analysis`.

## Tests added or modified

Added to `tests/acqstore/test_acq_analysis_set.py`:

- `test_get_analysis_resolves_by_class`
- `test_get_analysis_resolves_by_name_string`
- `test_get_analysis_missing_raises_key_error`
- `test_get_analysis_rejects_invalid_type`

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_acq_analysis_set.py -q
```

## Test results

```
19 passed in 0.90s
```

Linters: no errors on the changed source and test files.

## Concerns or follow-ups

- None. `get` / `get_required` are unchanged; existing callers (including
  cloudscope runtime) are unaffected.
