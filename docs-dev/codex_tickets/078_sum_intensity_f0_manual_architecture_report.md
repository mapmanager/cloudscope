# 078 Sum intensity F0 manual and architecture report

## Files changed

- `src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_core.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_analysis.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/README.md`
- `scripts/acqstore/try_sum_intensity_synthetic_analysis.py`
- `docs-dev/acqstore/analysis/sum_intensity_architecture.md`

## Summary of implementation

Added manual F0 support alongside percentile F0. Detection params now allow
`baseline_method='manual'` with `manual_f0_baseline`. The calculated F0 remains a
summary/result value, while detection params define how F0 is selected.

Updated the synthetic try script to show F0 on a normalized-intensity subplot,
while keeping df/f, derivative, peak markers, and width overlays together in the
main analysis plot.

Added a developer architecture document that records the stable backend design,
plotting primitives, F0 model, detection-param model, failure model, and event
feature roadmap.

## Tests added or modified

No tests were added in this focused replacement. Existing synthetic tests should
be updated in the next test-maintenance pass to cover `baseline_method='manual'`.

## Exact test commands run

```bash
uv run python -m py_compile \
  src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_core.py \
  src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_analysis.py \
  scripts/acqstore/try_sum_intensity_synthetic_analysis.py

uv run python - <<'PY'
from acqstore.acq_image.analysis.sum_intensity_analysis.sum_intensity_core import SumIntensityTraceKey, SumIntensitySummaryKey, run_sum_intensity
from acqstore.acq_image.analysis.sum_intensity_analysis.synthetic.synthetic_config import SyntheticSumIntensityConfig
from acqstore.acq_image.analysis.sum_intensity_analysis.synthetic.synthetic_generator import make_synthetic_sum_intensity_image
syn = make_synthetic_sum_intensity_image(SyntheticSumIntensityConfig(seed=1))
params = {
    'window_radius_points': 0,
    'filter_method': 'median',
    'median_filter_kernel_points': 3,
    'detrend_method': 'single_exponential',
    'baseline_method': 'manual',
    'baseline_percentile': 20.0,
    'manual_f0_baseline': 1000.0,
    'baseline_min_value': 1e-12,
    'detection_method': 'derivative_threshold',
    'polarity': 'positive',
    'detection_source': SumIntensityTraceKey.DF_F_SIGNAL.value,
    'absolute_threshold': 0.1,
    'derivative_threshold_per_sec': 3.0,
    'refractory_period_ms': 500.0,
    'peak_search_window_ms': 300.0,
    'width_search_window_ms': 900.0,
    'level_fractions': '0.1,0.2,0.5,0.8,0.9',
}
res = run_sum_intensity(syn.image, detection_params=params, physical_units=(syn.seconds_per_line, syn.um_per_pixel))
print(res.get_summary_value(SumIntensitySummaryKey.BASELINE_METHOD), res.get_summary_value(SumIntensitySummaryKey.F0_BASELINE))
print(res.get_trace(SumIntensityTraceKey.DF_F_SIGNAL).y[:3])
PY
```

## Test results

- Python compilation completed successfully.
- Synthetic manual-F0 smoke test completed successfully and printed `manual 1000.0`.

## Concerns or follow-ups

- Add focused pytest coverage for manual F0.
- Add event-feature tests once time-to-peak, pre-peak mean, AUC, rise tau, and
  decay tau are implemented.
- AUC and tau features require explicit event-stop and fit-window definitions
  before implementation.
