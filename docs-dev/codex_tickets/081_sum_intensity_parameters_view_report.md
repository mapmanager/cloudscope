# 081 Sum Intensity Parameters View Report

## Files changed

- `src/cloudscope/events/analysis.py`
- `src/cloudscope/controllers/analysis_controller.py`
- `src/cloudscope/views/view_ids.py`
- `src/cloudscope/views/left_toolbar_view.py`
- `src/cloudscope/views/sum_intensity_analysis_view.py`
- `tests/cloudscope/test_analysis_controller.py`
- `tests/cloudscope/test_left_toolbar_view.py`
- `tests/cloudscope/test_sum_intensity_analysis_view.py`

## Summary of implementation

Added first-pass single-selection CloudScope GUI integration for AcqStore sum-intensity analysis.

- Added `AnalysisKind.SUM_INTENSITY`.
- Allowed `AnalysisController` to validate, create, and run `sum_intensity` analyses through the existing single-analysis task path.
- Added `ViewId.SUM_INTENSITY_ANALYSIS`.
- Added `SumIntensityAnalysisView` as a left-toolbar panel view.
- Added a left-toolbar **Sum Intensity** tab.
- Built detection controls from `SumIntensityAnalysis.get_detection_schema()`.
- Built preset selection from `SumIntensityAnalysis.get_detection_presets()` and applied copied preset params through `get_detection_preset_params()`.
- Kept manual F0 as a normal detection-param edit through `baseline_method` and `manual_f0_baseline`.
- Added summary display for an existing selected `(file, channel, ROI)` sum-intensity analysis.
- Kept scope to single file/channel/ROI. Batch analysis and plot view integration are not included in this ticket.

## Tests added or modified

- Added `tests/cloudscope/test_sum_intensity_analysis_view.py`.
- Modified `tests/cloudscope/test_analysis_controller.py` for `SUM_INTENSITY` controller dispatch and worker behavior.
- Modified `tests/cloudscope/test_left_toolbar_view.py` for the new toolbar child view.

## Exact test commands run

The uploaded source zip did not include the root `README.md` expected by the editable build backend, so a temporary empty `README.md` was created only in the local test workspace before running tests.

```bash
touch README.md
uv run pytest tests/cloudscope/test_sum_intensity_analysis_view.py tests/cloudscope/test_analysis_controller.py tests/cloudscope/test_left_toolbar_view.py -q
```

## Test results

```text
38 passed in 6.46s
```

## Concerns or follow-ups

- This ticket intentionally does not add `SumIntensityPlotView`.
- This ticket intentionally does not add batch sum-intensity analysis.
- The current view keeps parameter state local to the view controls. A future ticket should add explicit CloudScope state/intent events for plot-driven parameter updates, for example threshold-line drag callbacks from `SumIntensityPlotView` updating the parameters view through controller-owned state.
- The method-filter visibility helper matches schema `methods` entries against current control values so it works across `filter_method`, `baseline_method`, and `detection_method` without hard-coding sum-intensity scientific parameter names in CloudScope.
