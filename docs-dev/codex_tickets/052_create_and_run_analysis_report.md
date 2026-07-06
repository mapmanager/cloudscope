# 052 — create_and_run analysis convenience

## Summary

Added `AcqAnalysisSet.create_and_run()` as a scripting convenience that creates
and runs one analysis in a single call. Callers may pass either a registered
analysis name string or an analysis class (for example
`RadonVelocityAnalysis`). The method validates inputs before mutating the
analysis set and supports optional partial `detection_params`, a
`replace_existing` flag, and an optional `execution_options` dict that is
forwarded to the analysis `set_execution_options` (for example
`{"use_multiprocessing": False}`, recommended inside Jupyter).

Updated `scripts/acqstore/try_acq_image_list.py` to demonstrate the simplified
scripting API, and updated `docs/notebooks/velocity-analysis.ipynb` to use
`create_and_run()` with `execution_options={"use_multiprocessing": False}`.

## Files changed

Added:

- `docs-dev/codex_tickets/052_create_and_run_analysis_report.md` — this report.

Modified:

- `src/acqstore/acq_image/acq_analysis_set.py` — added `create_and_run()` with
  `execution_options` passthrough.
- `scripts/acqstore/try_acq_image_list.py` — uses `create_and_run()`.
- `docs/notebooks/velocity-analysis.ipynb` — uses `create_and_run()` with
  `execution_options={"use_multiprocessing": False}`.
- `tests/acqstore/test_acq_analysis_set.py` — added `create_and_run` tests.

## Tests added or modified

Added to `tests/acqstore/test_acq_analysis_set.py`:

- create and run with class input
- create and run with name string input
- partial detection params merge
- duplicate identity raises when `replace_existing=False`
- `replace_existing=True` replaces and reruns
- missing data provider raises and leaves set unchanged
- invalid detection params raise before mutation
- unregistered analysis name raises `KeyError`
- invalid analysis argument type raises `TypeError`
- `execution_options` forwarded to `set_execution_options`
- unknown execution option raises before mutation
- `execution_options` on an analysis without the setter raises `TypeError`
- missing dependency raises and leaves set unchanged

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_acq_analysis_set.py -q
```

## Test results

- `27 passed` in 0.55s
- `uv run pytest tests/acqstore/test_acq_analysis_set.py tests/acqstore/test_analysis_detection_schema.py -q`

## Concerns or follow-ups

- `create()`, `get_or_create()`, and `run_analysis()` are unchanged; CloudScope
  controllers continue using the existing API.
- `execution_options` is forwarded verbatim to the analysis
  `set_execution_options`; keys are validated by that method (unknown keys
  raise `TypeError` before any mutation). Analysis types without a
  `set_execution_options` (for example event/heart-rate) raise `TypeError` when
  `execution_options` is supplied.
