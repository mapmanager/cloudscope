# Sum Intensity Flat Summary and Two-Column Params Report

## Files changed

- `src/cloudscope/views/analysis_summary_display.py`
- `src/cloudscope/views/sum_intensity_analysis_view.py`
- `src/cloudscope/views/velocity_analysis_view.py`
- `src/cloudscope/views/diameter_analysis_view.py`
- `src/acqstore/acq_image/analysis/sum_intensity_analysis/sum_intensity_analysis.py`
- `tests/cloudscope/test_analysis_summary_display.py`
- `tests/acqstore/acq_image/analysis/sum_intensity_analysis/test_sum_intensity_summary_values.py`
- `docs-dev/codex_tickets/sum_intensity_flat_summary_two_column_params_report.md`

## Summary of implementation

### Flat analysis summary in left-toolbar views

Added `build_analysis_summary_expansion_for_analysis()` which renders summary text from
`analysis.get_summary_values()` instead of raw `analysis.result.summary`.

Updated sum-intensity, velocity, and diameter analysis views to use the shared helper.
This removes the long `peak_events` dump from the sum-intensity Summary expansion while
keeping full summary data in backend storage.

Extended `SumIntensityAnalysis.summary_columns` with `detrend_method`, `detection_method`,
and `errors` so the flat GUI/pool projection includes the scalar fields users expect.

### Two-column detection parameters (sum intensity)

Detection parameters within each schema category now render in a two-column
`ui.grid`, following the same pattern as `SchemaCardWidget` /
`image_header_metadata_view` (`columns=2`, each control in a nested
`ui.column` with `gap-0 min-w-0 w-full`). Category headings and `pl-5` indent
are unchanged.

## Tests added or modified

- `tests/cloudscope/test_analysis_summary_display.py`
  - `test_build_analysis_summary_expansion_for_analysis_uses_flat_columns`
- `tests/acqstore/acq_image/analysis/sum_intensity_analysis/test_sum_intensity_summary_values.py`
  - `test_sum_intensity_get_summary_values_excludes_peak_events`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_analysis_summary_display.py tests/cloudscope/test_sum_intensity_analysis_view.py tests/acqstore/acq_image/analysis/sum_intensity_analysis/test_sum_intensity_summary_values.py -q
```

## Test results

All listed tests passed.

## Concerns or follow-ups

- Hidden method-filtered controls in the two-column grid may leave empty grid cells when
  toggled off; acceptable for now and consistent with metadata schema cards.
- Full `peak_events` remain available via `SumIntensityAnalysis.get_peak_events()` and
  the sum-intensity plot view.
