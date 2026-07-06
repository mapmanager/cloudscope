# 089 — Diameter detection param int coercion

## Files changed

- `src/cloudscope/views/diameter_analysis_view.py`
- `tests/cloudscope/test_diameter_analysis_view.py`

## Summary of implementation

Fixed diameter analysis detection-parameter collection so integer schema fields
(`window_rows_odd`, `stride`, `post_filter_kernel_size`) are coerced from
NiceGUI `ui.number` float values to Python `int` before
`DiameterAnalysis.validate_detection_params` runs.

Changes mirror the sum-intensity view fix, kept local to the diameter view
(diameter-only scope; no new shared module under `views/`).

- Added module-local `_coerce_detection_param_value`.
- INT controls use `ui.number(..., precision=0)`; FLOAT controls unchanged.
- `_current_detection_params` coerces visible control values using schema metadata.

## Tests added or modified

- `test_coerce_detection_param_value_converts_ui_number_float_to_int`
- `test_current_detection_params_coerces_int_fields_from_float_controls`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_diameter_analysis_view.py
```

## Test results

All tests in `tests/cloudscope/test_diameter_analysis_view.py` passed.

## Concerns or follow-ups

- Sum-intensity and velocity analysis views still carry similar local patterns;
  a future ticket could consolidate GUI↔schema coercion outside `views/` (e.g.
  under `nicewidgets/` or `cloudscope/gui/`) if cross-view reuse is desired.
