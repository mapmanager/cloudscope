# 047 - Heart Rate Plotting Helpers

## Summary

Added script/notebook-oriented plotting helpers for the new acqstore heart-rate
analysis. The plotting code lives under
`src/acqstore/acq_image/analysis/heart_rate_analysis/plotting/` and is separated
from the core analysis wrapper so backend analysis, persistence, and GUI code do
not import plotting modules unless callers explicitly ask for diagnostic plots.

The plotting helpers recompute preprocessing and spectra from the parent
velocity time-series. This is intentional because the persisted heart-rate
summary stores compact JSON values only and does not save raw spectral debug
arrays.

## Files changed

- Added `src/acqstore/acq_image/analysis/heart_rate_analysis/heart_rate_params.py`
  - shared conversion from serialized heart-rate `detection_params` to core
    estimator kwargs, including `bpm_min`/`bpm_max` and `edge_margin_hz=-1.0`
    sentinel handling.
- Updated `src/acqstore/acq_image/analysis/heart_rate_analysis/heart_rate_analysis.py`
  - analysis wrapper now uses `normalize_heart_rate_detection_params()` instead
    of duplicating parameter mapping.
- Added `src/acqstore/acq_image/analysis/heart_rate_analysis/plotting/__init__.py`
- Added `src/acqstore/acq_image/analysis/heart_rate_analysis/plotting/plot_data.py`
  - numpy-only diagnostic recomputation helpers for preprocessing, Welch PSD,
    Lomb-Scargle periodogram, and segment series.
- Added `src/acqstore/acq_image/analysis/heart_rate_analysis/plotting/mpl_plots.py`
  - matplotlib helpers for overview, Welch PSD, Lomb periodogram, segment
    series, and three-panel summary.
- Added `src/acqstore/acq_image/analysis/heart_rate_analysis/plotting/plotly_plots.py`
  - Plotly helpers returning `plotly.graph_objects.Figure` for overview, Welch
    PSD, Lomb periodogram, segment series, and three-panel summary.
- Updated `scripts/acqstore/try_heart_rate_analysis.py`
  - added `PLOT_RESULTS` and `USE_PLOTLY` switches.
  - default plotting path uses Plotly; matplotlib path remains available.
- Added `tests/acqstore/test_heart_rate_plotting.py`
  - tests plot-data recomputation and matplotlib/Plotly helper return values.

## Implementation details

- The `plotting/` folder is deliberately nested under the heart-rate analysis
  package to keep plotting helpers close to the analysis they diagnose while
  avoiding imports from `cloudscope`, `nicewidgets`, or NiceGUI.
- `plot_data.py` is numpy-only and shared by both matplotlib and Plotly modules.
- Plotly helpers return `go.Figure` objects for ergonomic script/notebook use.
- Matplotlib helpers import `matplotlib.pyplot` inside functions to keep module
  import side effects low.
- Plotting functions take `(time_s, velocity)` arrays plus optional
  `params=heart_rate.detection_params`, preserving array-based use in scripts
  and notebooks.

## Tests added or modified

Added `tests/acqstore/test_heart_rate_plotting.py`:

- `test_compute_preprocessing_defaults`
- `test_compute_spectra_recover_expected_frequency`
- `test_plotly_summary_returns_go_figure`
- `test_plotly_segment_series_returns_go_figure`
- `test_mpl_summary_returns_figure_and_axes`
- `test_mpl_segment_series_returns_axes`
- `test_compute_segment_series_has_expected_keys`

Existing heart-rate analysis tests were left intact and run together with the
new plotting tests.

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_heart_rate_analysis.py tests/acqstore/test_heart_rate_plotting.py -q
```

```text
15 passed, 10 warnings in 1.87s
```

```bash
uv run pytest tests/acqstore/ -q
```

```text
280 passed, 10 warnings in 2.61s
```

## Test results

All focused heart-rate tests and the full acqstore test suite passed.

The warnings are SciPy deprecation warnings for the existing Lomb-Scargle
`precenter` argument in the verbatim core. This remains unchanged to preserve
the original heart-rate algorithm behavior.

## Concerns or follow-ups

- Plotting recomputes spectra from velocity arrays and should be treated as a
  diagnostic view, not a source of persisted results.
- The Plotly default in `try_heart_rate_analysis.py` calls `fig.show()`, which
  may open a browser or notebook renderer depending on the environment.
- Phase 2 GUI work can reuse the Plotly helpers or the lower-level plot-data
  helpers, but no CloudScope GUI integration is included in this ticket.
