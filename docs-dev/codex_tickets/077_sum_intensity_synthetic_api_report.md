# 077 Sum intensity synthetic API report

## Files changed

- `src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_core.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_analysis.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/README.md`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/synthetic/__init__.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/synthetic/synthetic_config.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/synthetic/synthetic_data.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/synthetic/synthetic_events.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/synthetic/synthetic_generator.py`
- `scripts/acqstore/try_sum_intensity_synthetic_analysis.py`
- `tests/acqstore/acq_image/analysis/sum_intensity_analysis/test_sum_intensity_synthetic.py`

## Summary of implementation

Added a public synthetic-data utility package for sum-intensity analysis. The generator creates actual `(time, space)` images from a fluorescence model with difference-of-exponentials events, photobleaching, Gaussian noise, one-line pop artifacts, optional event jitter, and optional Poisson event timing.

Added plotting-friendly accessors to `SumIntensityCoreResult` so scripts and tests can use the same enum-backed trace/event/width API without an `AcqImage` wrapper.

Added a synthetic try script that runs the NumPy-only core algorithm and plots ground truth, df/f0, derivative, onset points, peak points, and width traces with Plotly.

Updated the package README with synthetic utility documentation.

## Tests added or modified

Added `test_sum_intensity_synthetic.py` covering:

- synthetic image shape and ground-truth event table
- core analysis on synthetic images
- enum-backed trace, event-point, and width-trace accessors
- width-search-window failure behavior
- deterministic Poisson event generation

## Exact test commands run

```bash
uv run pytest tests/acqstore/acq_image/analysis/sum_intensity_analysis/test_sum_intensity_synthetic.py
```

## Test results

```text
4 passed
```

## Concerns or follow-ups

- The synthetic event model is intentionally simple and public. It should remain deterministic for tests and can be expanded later with vessel-like spatial profiles or more baseline models if needed.
- The synthetic script uses Plotly directly as a stand-in for the future `PlotlyPlotWidget` API.
