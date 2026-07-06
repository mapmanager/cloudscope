# Analysis summary float rounding in GUI display

## Files changed

- `src/cloudscope/views/analysis_summary_display.py`
- `tests/cloudscope/test_analysis_summary_display.py`

## Summary of implementation

- Added `_format_summary_value()` to round `float` and `numpy.floating` summary values to three decimal places at display time, stripping trailing zeros (e.g. `7.2`, not `7.200`).
- `nan` and `inf` are left as Python default strings.
- `int`, `bool`, and `str` values are unchanged.
- `format_analysis_summary_lines()` now uses the helper; velocity and diameter views are unchanged.

## Tests added or modified

- Modified: `tests/cloudscope/test_analysis_summary_display.py`
- Added: `test_format_analysis_summary_lines_rounds_floats`
- Added: `test_format_analysis_summary_lines_non_finite_floats`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_analysis_summary_display.py
```

## Test results

- 4 passed

## Concerns or follow-ups

- Heart-rate and event analysis views do not yet use this helper; they can adopt it later when summary panels are added.
