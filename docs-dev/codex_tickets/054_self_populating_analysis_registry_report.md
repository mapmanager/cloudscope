# 054 Self-Populating Analysis Registry Report

## Files changed

- `src/acqstore/acq_image/analysis/registry.py`
- `src/acqstore/acq_image/analysis/examples.py`
- `scripts/acqstore/try_acq_analysis.py`
- `tests/acqstore/test_analysis_registry.py`
- `tests/acqstore/test_analysis_detection_schema.py`
- `tests/acqstore/test_analysis_dirty.py`
- `tests/acqstore/test_analysis_dependencies.py`
- `tests/acqstore/test_analysis_events.py`
- `docs/notebooks/velocity-analysis.ipynb`
- `docs/notebooks/diameter-analysis.ipynb`
- `docs/notebooks/heart-rate-analysis.ipynb`
- `docs/notebooks/load-and-plot-image.ipynb`

## Summary of implementation

- Added self-populating built-in analysis registration so `get_analysis_class()` and
  `get_analysis_registry()` can resolve production analyses without caller-side
  imports for registration side effects.
- Removed the obsolete `examples.py` analysis fixtures from `src/acqstore`.
- Retargeted tests and the analysis exercise script to production analysis classes.
- Removed notebook registration workaround comments/imports and replaced remaining
  notebook default channel/ROI access with explicit channel/ROI list selection.

## Tests added or modified

- Added `tests/acqstore/test_analysis_registry.py`.
- Updated detection schema, dependency, and dirty-state tests to avoid
  `analysis.examples`.
- Removed the circular `tests/acqstore/test_analysis_events.py` fixture tests.

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_analysis_registry.py tests/acqstore/test_analysis_detection_schema.py tests/acqstore/test_analysis_dirty.py tests/acqstore/test_analysis_dependencies.py tests/acqstore/test_heart_rate_analysis.py
```

## Test results

```text
27 passed, 4 warnings in 0.95s
```

## Concerns or follow-ups

- Notebook outputs were not re-executed. `load-and-plot-image.ipynb` still contains
  stale saved output from before this fix; it should disappear on the next notebook
  run.
