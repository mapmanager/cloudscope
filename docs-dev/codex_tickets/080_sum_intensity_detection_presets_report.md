# 080 Sum Intensity Detection Presets Report

## Files changed

- `src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_presets.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_analysis.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/README.md`
- `docs-dev/acqstore/analysis/sum_intensity_architecture.md`
- `scripts/acqstore/try_sum_intensity_analysis.py`
- `tests/acqstore/acq_image/analysis/sum_intensity_analysis/test_sum_intensity_presets.py`

## Summary of implementation

Added first-class AcqStore sum-intensity detection presets. Presets are backend-native, enum-backed, immutable descriptors that return copied complete detection-parameter dictionaries. Built-in presets are `fast`, `medium`, and `slow`.

Manual F0 remains a normal detection-parameter workflow, not a preset. GUI code should set `baseline_method='manual'` and `manual_f0_baseline=<dragged value>` when the user chooses manual F0.

The `SumIntensityAnalysis` wrapper now exposes class-level preset helpers for GUI and scripting callers:

- `get_detection_presets()`
- `get_detection_preset(name)`
- `get_detection_preset_params(name)`

The try script now consumes the backend preset API instead of defining local preset dictionaries.

## Tests added or modified

Added:

- `tests/acqstore/acq_image/analysis/sum_intensity_analysis/test_sum_intensity_presets.py`

The tests verify preset order, enum lookup, fail-fast unknown names, schema compatibility, copied parameter dictionaries, class wrapper helpers, and synthetic core execution with the medium preset.

## Exact test commands run

```bash
uv run pytest tests/acqstore/acq_image/analysis/sum_intensity_analysis/test_sum_intensity_presets.py -q
uv run pytest tests/acqstore/test_sum_intensity_core.py tests/acqstore/test_sum_intensity_analysis.py tests/acqstore/acq_image/analysis/sum_intensity_analysis/test_sum_intensity_synthetic.py tests/acqstore/acq_image/analysis/sum_intensity_analysis/test_sum_intensity_presets.py -q
```

## Test results

- `5 passed` for the focused preset test file.
- `19 passed` for the focused sum-intensity test set.

## Concerns or follow-ups

- Preset numeric values are initial backend defaults and should be tuned with more biological datasets.
- Manual F0 is intentionally not a preset; it remains an explicit parameter edit in the future GUI.
- No `__init__.py` files were modified.
