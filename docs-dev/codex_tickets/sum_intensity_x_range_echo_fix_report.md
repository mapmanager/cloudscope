# X-range sync echo loop fix report

## Files changed

- `src/cloudscope/events/x_range.py` — shared `x_ranges_equal`
- `src/cloudscope/controllers/x_range_controller.py`
- `src/nicewidgets/echart_widget/widget.py` (root fix for acq EChart)
- `src/cloudscope/views/acq_analysis_plot_view.py`
- `src/cloudscope/views/sum_intensity_plot_view.py`
- `src/cloudscope/views/primary_image_view.py`
- `src/nicewidgets/plotly_plot/widget.py`
- `tests/cloudscope/test_x_range_view_wiring.py`
- `tests/nicewidgets/test_echart_x_range.py`

## Summary of implementation

### Root cause (case 2 — acq analysis EChart)

The one-shot `_chart_originated_x_range` flag was insufficient. A single user
zoom produces **multiple** datazoom events and async relayout echoes from other
views. After the first `PrimaryXRangeChanged` cleared the flag, later echoes
could still:

1. Re-publish `SetPrimaryXRangeIntent` (duplicate datazoom / async Plotly
   relayout from other consumers)
2. Call `set_x_axis_limits` → `apply()` on the acq chart
3. Fire more datazoom → non-terminating loop

Case 1 worked because `PrimaryImageView` combined origin skipping **and** the
raster viewer's strong echo dedup. Case 2 lacked both durable state sync on the
EChart widget and producer-side "already in app state" suppression.

### Fixes

1. **`EChartWidget`**
   - Sync `_x_range` on user datazoom (without `apply()`)
   - Suppress duplicate datazoom when range equals current logical `_x_range`
   - `set_x_axis_limits` no-op when logical range unchanged (skip `apply()`)
   - Expose `x_range_limits` property

2. **All three producer views** (`PrimaryImageView`, `AcqAnalysisPlotView`,
   `SumIntensityPlotView`)
   - Do not publish intent when callback range already equals cached
     `_primary_x_range` (blocks async relayout / duplicate datazoom republish)

3. **`AcqAnalysisPlotView` consumer**
   - Skip `set_x_axis_limits` when chart `x_range_limits` already matches
     `_primary_x_range`
   - Retain `_chart_originated_x_range` skip

4. **Shared `x_ranges_equal`** in `cloudscope.events.x_range` (used by controller
   and views)

## Tests added or modified

- `test_datazoom_suppressed_when_logical_range_unchanged`
- `test_set_x_axis_limits_skips_apply_when_range_unchanged`
- `test_acq_analysis_plot_view_does_not_republish_when_cache_matches`
- Updated wiring tests for state-aware publish suppression

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_x_range_view_wiring.py tests/cloudscope/test_x_range_controller.py tests/nicewidgets/test_echart_x_range.py tests/cloudscope/test_sum_intensity_plot_view.py tests/nicewidgets/test_plotly_plot_widget.py -q
```

## Test results

66 passed in 1.55s

## Concerns or follow-ups

- Manual browser verification of acq-chart zoom (case 2) still recommended.
