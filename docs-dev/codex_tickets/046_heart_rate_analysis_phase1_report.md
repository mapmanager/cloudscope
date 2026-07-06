# 046 — Heart Rate Analysis (Phase 1: acqstore backend)

## Summary

Implemented heart-rate analysis as a first-class `acqstore` analysis. Heart rate
is computed from the velocity time-series of a required parent `radon_velocity`
analysis for the same `(channel, roi_id)`. The analysis produces a single
JSON-serializable summary dictionary and no CSV table, so persistence is handled
entirely by the existing AcqImage sidecar JSON (`detection_params` + `summary`).

The numeric core was ported verbatim from `sandbox/heart_rate/heart_rate_analysis.py`
(no algorithmic change). The sandbox dataframe/CSV pipeline
(`heart_rate_pipeline.py`) was replaced by a thin `BaseAnalysis` wrapper that
follows the same pattern as `EventAnalysis` (dependent analysis consuming the
parent's `get_plot_data()`).

This covers Phase 1 only. GUI work (Phase 2) is not included.

## Design decisions (confirmed with user)

- Detection params: `bpm_band` split into `bpm_min` / `bpm_max` (FLOAT);
  `edge_margin_hz` uses sentinel `-1.0` meaning "auto" (mapped to `None`).
- Methods: both `lombscargle` and `welch` are run on every call, with an
  agreement block.
- Segments: `do_segments` defaults OFF. When enabled, only a compact
  `segments_summary` is stored (`n_windows`, `n_valid_windows`, `median_bpm`,
  `iqr_bpm`) — never raw segment arrays.
- Naming: `analysis_name = "heart_rate"`; the unused `velocity_heart_rate`
  example stub was removed from `examples.py`.
- `get_plot_data()` returns `None` for Phase 1 (HR has no canonical x/y line).

## Summary schema (version 1)

Top-level keys: `version`, `n_total`, `n_valid`, `valid_frac`, `t_min`, `t_max`,
`lomb`, `welch`, `agreement`, `status`, `status_note`. Optional
`segments_summary` when `do_segments=True`.

Each of `lomb` / `welch` is a block: `method`, `bpm`, `f_hz`, `snr`,
`edge_flag`, `edge_hz_distance`, `band_concentration`, `n_samples`, `n_valid`,
`t_start`, `t_end`, `status`, `status_note`, `reason`. Numeric fields are `null`
when the method produced no estimate. `agreement` is `null` when either method
lacks a bpm; otherwise `delta_bpm`, `abs_delta_bpm`, `delta_hz`, `agree_ok`,
`agree_tol_bpm`. Top-level `status` is the cross-method rollup (`ok`,
`insufficient_valid`, `no_peak_lomb`, `no_peak_welch`, `method_disagree`,
`other_error`). Numpy debug arrays are intentionally excluded.

## Files changed

- Added `src/acqstore/acq_image/analysis/heart_rate_analysis/__init__.py`
- Added `src/acqstore/acq_image/analysis/heart_rate_analysis/heart_rate_core.py`
  (verbatim core estimators: `estimate_heart_rate_global`,
  `estimate_heart_rate_segment_series`, `HeartRateEstimate`, `HRStatus`, plus
  preprocessing/spectral helpers).
- Added `src/acqstore/acq_image/analysis/heart_rate_analysis/heart_rate_analysis.py`
  (`HeartRateAnalysis(BaseAnalysis)` wrapper, detection schema, summary builder,
  agreement/status classification, JSON load).
- Modified `src/acqstore/acq_image/analysis/examples.py`
  (removed the unused `VelocityHeartRateAnalysis` example stub).
- Added `scripts/acqstore/try_heart_rate_analysis.py`
  (velocity -> heart-rate workflow with sampling diagnostics, save/reload).
- Added `tests/acqstore/test_heart_rate_analysis.py`.

## Tests added

`tests/acqstore/test_heart_rate_analysis.py`:

- `test_heart_rate_registered`
- `test_detection_schema_defaults`
- `test_run_estimates_expected_heart_rate` (synthetic 360 bpm series via the
  analysis set, both methods, agreement)
- `test_run_marks_dirty_and_has_no_table`
- `test_insufficient_samples_reports_status`
- `test_missing_dependency_raises`
- `test_segments_summary_present_when_enabled`
- `test_json_roundtrip_preserves_summary`

## Test commands and results

```bash
uv run pytest tests/acqstore/test_heart_rate_analysis.py -q
# 8 passed

uv run pytest tests/acqstore/ -q
# 273 passed, 4 warnings
```

The 4 warnings are a SciPy `lombscargle(precenter=...)` deprecation originating
from the verbatim core; left unchanged to keep the core numerically identical to
the sandbox source.

## Concerns / follow-ups

- Sampling sufficiency: `radon_velocity` emits one sample per analysis window
  (25% overlap; `stepsize = window_width / 4`), so the velocity series feeding HR
  is shorter/slower than a raw per-line trace. The core requires `n_valid >= 256`,
  so HR needs a sufficiently long recording. `try_heart_rate_analysis.py` prints
  `n_valid` and the effective sample rate so this can be verified on real data.
- `use_abs` defaults to `True` (sandbox default). For a clean bipolar sine this
  doubles the apparent frequency; real velocity traces are the intended input.
- Phase 2 (GUI / results display) is intentionally out of scope and will be
  planned separately.
```
