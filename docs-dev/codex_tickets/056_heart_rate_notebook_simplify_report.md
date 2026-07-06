# 056 — Simplify heart-rate-analysis notebook

## Summary

Aligned `docs/notebooks/heart-rate-analysis.ipynb` with the patterns established in
the recently simplified velocity and diameter notebooks:

1. **Schema display** — replaced manual list comprehension with
   `HeartRateAnalysis.get_detection_schema_dataframe()`.
2. **Run analysis** — removed the `run_heart_rate` helper (`get_or_create` +
   `set_detection_params` + `run_analysis`) and inlined
   `acq.analysis_set.create_and_run(HeartRateAnalysis, ...)` for both accept and
   reject cases.
3. **Save/load** — added a runnable save/load cell using `acq.save()`,
   `AcqImage(acq.path)`, and `get_analysis(HeartRateAnalysis, channel=, roi_id=)`.
   Split takeaways into a separate markdown cell (matching velocity/diameter).

Heart-rate-specific helpers were intentionally kept:

- `get_velocity` — ensures the required `radon_velocity` input exists (reuses saved
  analysis or runs Radon only when needed).
- `velocity_diagnostics` — teaches sampling requirements for heart rate.
- `verdict` — accept/reject domain logic central to this notebook.

Also added `AcqImage` import to the imports cell (needed for save/load).

## Files changed

- `docs/notebooks/heart-rate-analysis.ipynb`

## Tests added or modified

None (notebook-only change).

## Exact test commands run

None required for notebook-only documentation changes.

## Test results

N/A

## Concerns or follow-ups

- None. No source API changes.
