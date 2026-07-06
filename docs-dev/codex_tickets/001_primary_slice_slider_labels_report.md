# 001 — Primary image T/Z slice slider labels

## Files changed

- `src/cloudscope/views/primary_image_view.py`
- `tests/cloudscope/test_primary_image_view.py`

## Summary of implementation

- Added `format_slice_slider_display()` for 1-based display-only counter text
  (`0/9` internally → `1/10` in the UI).
- Restructured `_slice_row` into per-axis groups (`_t_group`, `_z_group`), each
  with static axis label (`T` / `Z`), slider, and trailing counter label.
- Removed Quasar `label="T"` / `label="Z"` slider props.
- `_sync_slice_sliders_from_header()` and `_hide_slice_sliders()` show/hide
  entire groups and refresh counter text on file/header sync.
- `_on_t_slider_changed` / `_on_z_slider_changed` update counter labels on drag.

## Tests added or modified

- `test_format_slice_slider_display` in `tests/cloudscope/test_primary_image_view.py`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_primary_image_view.py::test_format_slice_slider_display -q
uv run pytest tests/cloudscope/test_primary_image_view.py -q
```

## Test results

- `test_format_slice_slider_display`: 1 passed
- Full `test_primary_image_view.py`: all passed

## Follow-up plan: hide `_slice_row` when both groups hidden

**Goal:** Remove the residual empty vertical strip from `_slice_row` padding
(`py-1`) when neither T nor Z stack controls are visible.

**Approach:**

1. After `_apply()` in `_sync_slice_sliders_from_header()` and in
   `_hide_slice_sliders()`, call a small helper e.g.
   `_sync_slice_row_visibility()` that:
   - Shows `_slice_row` when at least one of `_t_group` / `_z_group` is visible
     (not `hidden`).
   - Hides `_slice_row` (add `hidden`, remove shrink/padding classes or use
     `set_visibility(False)`) when both groups are hidden.
2. Ensure `_slice_row` starts hidden in `build()` if both groups start hidden
   (matches current default).
3. Browser-verify on:
   - Y/X-only file (no strip)
   - T-only / Z-only / T+Z files (row visible with controls)
   - Deselect file (row hidden again)
4. Add a focused unit test if feasible (mock groups + assert helper toggles
   row classes); otherwise rely on browser check per GUI rule.

**Friction:** `_slice_row` uses `shrink-0`; hiding it must not affect plot
flex layout (`flex-1` plot area should reclaim space cleanly).

## Concerns or follow-ups

- Manual browser verification on multi-T / multi-Z sample data recommended.
- Follow-up ticket above for collapsing `_slice_row` when both axes absent.
