# 061 — Skip guard for untracked OIR fixture on CI

## Problem

The GitHub Actions `Tests` workflow failed on `main` with:

```text
FAILED tests/acqstore/test_oir_file_loader.py::test_oir_debug_0010_reference_image_metadata_matches_primary_x
FileNotFoundError: ... tmp/oir-debug/two-channel-oir/20260709_A131_0010.oir
```

The test reads a raw OIR file under `tmp/` that is intentionally not git
tracked (`tmp/` is gitignored). It passed locally but failed on CI where the
file does not exist. Every other test in the file that touches a local raw
data file already carries a `@pytest.mark.skipif(not <path>.is_file(), ...)`
guard; this one (added in ticket 058/059 work) was missing the guard.

## Files changed

- `tests/acqstore/test_oir_file_loader.py` — added the standard skipif guard
  (same decorator already used by `test_oir_debug_0010_reference_matches_primary_x_and_txt_um_per_pixel`)
  to `test_oir_debug_0010_reference_image_metadata_matches_primary_x`, and
  restored the two blank lines between test functions.

## Summary of implementation

One-decorator fix following the existing pattern in the same file:

```python
@pytest.mark.skipif(not _OIR_DEBUG_0010.is_file(), reason="oir-debug 0010 missing")
def test_oir_debug_0010_reference_image_metadata_matches_primary_x() -> None:
```

## Tests added or modified

No new tests; guard added to one existing test.

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_oir_file_loader.py -q
# CI simulation: temporarily moved the fixture aside and re-ran
uv run pytest tests/acqstore/test_oir_file_loader.py -q -rs
uv run pytest -q
```

## Test results

- Focused file with fixture present: 20 passed.
- Focused file with fixture moved aside (CI simulation): 18 passed, 2 skipped
  (both 0010 tests skip with "oir-debug 0010 missing"); fixture restored after.
- Full suite: 1990 passed, 1 skipped, 17 warnings.

## Concerns or follow-ups

- Recurring failure mode: tests that open local raw data files (tif/oir/nd2)
  slip through without a skip guard because the files exist locally. A future
  ticket could add an automated guard (e.g. a meta-test or pre-push check that
  runs pytest against a clean `git archive` checkout) to catch these before
  they reach CI.
