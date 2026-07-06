# Sum intensity exclusive-group fix report

## Files changed

- `src/cloudscope/controllers/analysis_controller.py`
- `tests/cloudscope/test_analysis_controller.py`
- `tests/acqstore/test_analysis_exclusion.py`

## Summary of implementation

The controller pre-flight gate `_validate_intent` was calling
`_raise_if_exclusive_conflict` for every non-EVENT analysis kind, including
`SUM_INTENSITY`. That incorrectly blocked sum-intensity runs when
`radon_velocity` or `diameter` already existed for the same `(channel, roi_id)`.

AcqStore already allows coexistence: `SumIntensityAnalysis.exclusive_group` is
`None`; only radon and diameter share `primary_kymograph`.

**Fix:** Run the exclusive-conflict check only for `RADON_VELOCITY` and
`DIAMETER`.

## Tests added or modified

- `test_analysis_controller_allows_sum_intensity_when_diameter_exists`
- `test_sum_intensity_coexists_with_diameter_for_same_roi`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_analysis_controller.py tests/acqstore/test_analysis_exclusion.py -q
```

## Test results

35 passed in 0.73s

## Concerns or follow-ups

- X-axis sync feedback loop involving `SumIntensityPlotView` is tracked
  separately; see chat plan for echo-suppression fix.
