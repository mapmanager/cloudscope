# 013 Filter signal interpolate through nan report

## Files changed

- `src/acqstore/common_analysis/dff0_diameter_analysis/preprocessing.py`
- `src/acqstore/common_analysis/dff0_diameter_analysis/tests/test_preprocessing.py`

## Summary of implementation

Implemented plan B (interpolate-through) for `filter_signal`:

- Removed the blanket `ValueError` on input NaN.
- Added `_fill_nan_1d` to linearly interpolate missing samples before filtering.
- **NONE** — still returns a copy with NaN preserved.
- **MEDIAN / SAVGOL** — fill gaps, then apply `scipy` filter; output is finite when any input sample is finite; all-NaN input returns zeros.
- Expanded `filter_signal` docstring documenting previous vs current return semantics.

## Tests added or modified

- Added `tests/test_preprocessing.py` with five unit tests for NONE passthrough, median/SG interpolate-through, all-NaN edge case, and finite-only regression.

## Exact test commands run

```bash
uv run pytest src/acqstore/common_analysis/dff0_diameter_analysis/tests/ -q
```

## Test results

10 passed.

## Concerns or follow-ups

- Triggered-event metrics may now succeed in windows that previously failed when NaN blocked filtering entirely; compare event status on real data with missing diameter samples.
- `triggered_events` extremum search on arrays containing NaN (if filter_method is NONE) remains a separate follow-up.
