# 011 — Skip ABF fixture tests when sample data is missing

## Problem

New `acq_trace` / ABF tests open files under `tests/acqstore/data/abf/`, which is
gitignored (same as `oir-samples`, `czi-samples`, `tif-samples`). GitHub Actions
does not have those files, so pytest failed with `FileNotFoundError` instead of
skipping.

Existing OIR integration tests already use `@pytest.mark.skipif(not path.is_file(), ...)`.
CZI/TIF unit tests avoid the issue by using mocks or synthetic `tmp_path` files.

## Summary of implementation

Mirror the OIR optional-fixture pattern for ABF:

- Define a local `requires_abf` skip marker in each ABF test module (same style as
  OIR; no shared import from `conftest` because `tests.acqstore` is not on
  `pythonpath`).
- Mark every test that opens a real ABF under `tests/acqstore/data/abf`.
- Leave always-on unit tests unmarked (path validation, synthetic peak core,
  `TraceHeader` / `EpochTable` / `SweepData` construction).

No production code changes. Sample ABF binaries remain untracked.

## Files changed

- `tests/acqstore/test_abf_trace_loader.py`
- `tests/acqstore/test_acq_trace.py`
- `tests/acqstore/test_acq_trace_peak_detection.py`
- `docs-dev/cursor_tickets/011_skip_abf_fixture_tests_report.md`

## Tests added or modified

- Modified: ABF-dependent tests now use `@requires_abf`.
- Unchanged behavior when fixtures are present.

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_abf_trace_loader.py \
  tests/acqstore/test_acq_trace.py \
  tests/acqstore/test_acq_trace_peak_detection.py -q --tb=no
```

Simulated CI (fixtures temporarily renamed away):

```bash
mv tests/acqstore/data/abf tests/acqstore/data/abf.bak
uv run pytest tests/acqstore/test_abf_trace_loader.py \
  tests/acqstore/test_acq_trace.py \
  tests/acqstore/test_acq_trace_peak_detection.py -q --tb=line
mv tests/acqstore/data/abf.bak tests/acqstore/data/abf
```

## Test results

- With local ABF fixtures: **43 passed**
- Without ABF fixtures (CI simulation): **14 passed, 29 skipped** (no failures)

## Concerns or follow-ups

- Golden-file ABF coverage still runs only on machines that have
  `tests/acqstore/data/abf`. That matches OIR optional fixtures.
- If CI ever needs real ABF coverage, register a small public sample via
  `acqstore.sample_data` rather than committing binaries under `tests/acqstore/data`.
