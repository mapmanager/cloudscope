# 076 Sum Intensity Analysis Report

## Files changed

- `src/acqstore/acq_image/analysis/registry.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/__init__.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/README.md`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_analysis.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_core.py`
- `scripts/acqstore/try_sum_intensity_analysis.py`
- `tests/acqstore/test_sum_intensity_analysis.py`
- `tests/acqstore/test_sum_intensity_core.py`

## Summary of implementation

Implemented a backend-only `sum_intensity` analysis under `src/acqstore/acq_image/analysis/`.
The implementation follows the existing `BaseAnalysis` wrapper plus pure-core pattern used by diameter and velocity analyses.

The analysis pipeline is:

1. Receive a 2D ROI image shaped `(time, space)` from `AnalysisDataProvider`.
2. Compute vectorized row sums over space.
3. Apply optional clipped-edge rolling mean using `window_radius_points`.
4. Compute `norm_sum_intensity = sum_intensity / image.shape[1]`.
5. Optionally median-filter normalized intensity, default kernel 3.
6. Try single-exponential detrending with `scipy.optimize.curve_fit`.
7. If detrending fails, record an analysis-level error and continue with the filtered normalized trace.
8. Compute derivative with `np.gradient(detection_signal, time_sec)`.
9. Detect onsets by derivative threshold by default, with absolute-threshold support.
10. Enforce onset-to-onset refractory period.
11. Refine peaks inside `peak_search_window_ms`.
12. Extract per-peak event records and level-crossing width measurements for fractions `0.1,0.2,0.5,0.8,0.9`.
13. Store one row per timepoint in the result table and event records in summary JSON.

Also added:

- Builtin registry registration for `sum_intensity`.
- A package-local README documenting the algorithm, vectorized row-sum performance rationale, failure model, and CSV columns.
- A Plotly exercise script at `scripts/acqstore/try_sum_intensity_analysis.py`.

This corrected replacement intentionally does **not** modify root `README.md`, `src/acqstore/acq_image/analysis/__init__.py`, or `tests/acqstore/test_public_imports.py`.

## Tests added or modified

Added:

- `tests/acqstore/test_sum_intensity_core.py`
- `tests/acqstore/test_sum_intensity_analysis.py`

Coverage includes:

- Vectorized rolling row-sum equivalence and normalization by `image.shape[1]`.
- Derivative-threshold onset detection and peak refinement.
- Level-crossing failure recorded as data.
- `curve_fit` detrend failure fallback recorded in summary errors without runtime failure.
- `PeakEvent` JSON round trip.
- `BaseAnalysis` wrapper result, plot, registry, and `AcqAnalysisSet` orchestration.

## Exact test commands run

A local placeholder `README.md` was used only inside the sandbox test workspace because the uploaded source zip lacks the file required by `pyproject.toml` (`readme = "README.md"`). This placeholder is not included in the replacement zip.

```bash
uv run pytest tests/acqstore/test_sum_intensity_core.py tests/acqstore/test_sum_intensity_analysis.py
```

```bash
uv run pytest
```

## Test results

Focused sum-intensity tests:

```text
9 passed in 0.10s
```

Full test suite:

```text
1477 passed, 17 skipped, 13 warnings in 26.35s
```

## Concerns or follow-ups

- `DetectionParamSchema` currently supports scalar-like values only. `level_fractions` is therefore stored as a comma-separated string. This works for first pass but a future schema enhancement could support list/tuple numeric params directly.
- Event records are currently stored in the analysis summary JSON. If files contain very large event counts, we may eventually want a dedicated event JSON sidecar or event table.
- The first pass keeps peak detection inside the sum-intensity package. Promote to a reusable `peak_detection/` package only after another analysis needs it.
- Future GUI work should add a thin CloudScope 1D EChart view over this backend API.
- Future pool work should use one row per `(acqimage, channel, roi, peak/event)`, not one row per `(acqimage, channel, roi)` like the current velocity pool.
