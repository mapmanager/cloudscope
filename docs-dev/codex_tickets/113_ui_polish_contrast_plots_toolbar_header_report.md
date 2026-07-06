# 113 — UI polish: contrast seeding, plot labels, toolbar, header Save

## Files changed

- `src/cloudscope/contrast_seeding.py` — NEW: shared contrast percentile/LUT/seed helpers
- `src/cloudscope/plot_axis_labels.py` — NEW: `kymograph_time_x_label()` from image header
- `src/cloudscope/views/app_config_view.py` — editable auto-contrast percentile fields
- `src/cloudscope/views/primary_image_view.py` — `app_config`; seed contrast before first apply
- `src/cloudscope/views/reference_image_view.py` — `app_config`; configurable reference percentiles
- `src/cloudscope/views/left_toolbar_view.py` — pass `app_config` to reference image panel
- `src/cloudscope/views/image_toolbar_view.py` — use shared contrast seeding helper
- `src/cloudscope/pages/home_page.py` — pass `app_config` to `PrimaryImageView`
- `src/cloudscope/views/acq_analysis_plot_view.py` — apply x/y axis labels (x from header)
- `src/cloudscope/views/sum_intensity_plot_view.py` — x label from header
- `src/cloudscope/views/load_save_view.py` — compact `grid-cols-2` load/save layout
- `src/nicewidgets/image_toolbar_widget/image_toolbar_widget.py` — narrow selects; disable singletons
- Tests: `test_contrast_seeding.py`, `test_plot_axis_labels.py`, updated app config / reference / toolbar / acq plot tests

## Summary

**Ticket 1 (contrast):** AppConfig percentiles exposed in App Settings UI. Primary image seeds contrast from plane + channel LUT **before** `_apply_contrast` (fixes gray LUT on first load, no new events). Left-toolbar reference image uses same percentiles via `reference_contrast_window(..., percentile_low/high)`.

**Ticket 2 (plot labels):** `AcqAnalysisPlotView` and `SumIntensityPlotView` set x-axis label from `physical_label_y` when non-empty; y-axis unchanged from analysis `plot_data`.

**Ticket 3 (toolbar):** Channel/ROI selects `w-14`; disabled when only one option (value still shown).

**Ticket 4 (header):** Compact Load/Save uses two-column grid; save buttons in right half.

## Tests added or modified

- `tests/cloudscope/test_contrast_seeding.py`
- `tests/cloudscope/test_plot_axis_labels.py`
- `tests/cloudscope/test_app_config_view.py`
- `tests/cloudscope/test_reference_image_view.py`
- `tests/cloudscope/test_acq_analysis_plot_view.py`
- `tests/nicewidgets/test_image_toolbar_widget_handlers.py`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_contrast_seeding.py tests/cloudscope/test_plot_axis_labels.py tests/cloudscope/test_app_config_view.py tests/cloudscope/test_reference_image_view.py tests/nicewidgets/test_image_toolbar_widget_handlers.py tests/cloudscope/test_image_toolbar_view.py tests/cloudscope/test_app_config_contrast.py tests/cloudscope/test_acq_analysis_plot_view.py -q
```

## Test results

82 passed.

## Concerns or follow-ups

- Future acqstore ticket could map header strings (e.g. `"seconds"` → `"Time (s)"`) inside `get_plot_data()`.
- Home-page reference image (commented out) can reuse same `app_config` wiring when restored.
