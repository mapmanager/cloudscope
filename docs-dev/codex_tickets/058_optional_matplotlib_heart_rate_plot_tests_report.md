# 058 — Optional Matplotlib heart-rate plot tests

## Files changed

- `tests/acqstore/test_heart_rate_plotting.py`

## Summary of implementation

Fixed GitHub Actions test collection when Matplotlib is not installed. The
heart-rate plotting test file previously imported `matplotlib` at module import
time, but Matplotlib is intentionally only included in the docs dependency group,
not the default/dev test environment.

The Matplotlib import is now gated inside the two Matplotlib-specific tests with
`pytest.importorskip("matplotlib")`. The numpy-only diagnostic-data tests and
Plotly plotting tests still run normally in the default CI environment.

## Tests added or modified

- Modified `test_mpl_summary_returns_figure_and_axes`.
- Modified `test_mpl_segment_series_returns_axes`.
- No new tests added.

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_heart_rate_plotting.py -q
```

## Test results

```text
8 passed, 8 warnings in 17.42s
```

The warnings are SciPy `precenter` deprecation warnings from Lomb-Scargle usage;
they are unrelated to the Matplotlib collection fix.

## Concerns or follow-ups

- On GitHub Actions, where Matplotlib is not installed, the two Matplotlib tests
  should be skipped instead of failing during collection.
- No source code changes were required.
