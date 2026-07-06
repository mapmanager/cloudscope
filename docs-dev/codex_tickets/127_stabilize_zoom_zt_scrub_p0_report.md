# 127 — Stabilize zoom + Z/T scrub (P0)

## Files changed

- `src/cloudscope/views/primary_image_view.py`
- `tests/cloudscope/test_primary_image_view.py`
- `docs-dev/codex_tickets/127_stabilize_zoom_zt_scrub_p0_report.md`

## Summary

- Path B (Z/T scrub, `include_overlays=False`) no longer calls `_apply_primary_x_range_to_viewer` after `set_data`. That x-only re-apply left inconsistent viewport state after a full data reset and matched reported double-click / Z-slider failures after zoom+scrub.
- Z/T scrubs now carry a `slice_generation` token; stale in-flight reloads are dropped when the user scrubs again before the prior load finishes.

## Tests added or modified

- `test_slice_refresh_schedules_plane_only_reload`
- `test_slice_refresh_skips_primary_x_range_reapply`
- `test_stale_slice_refresh_is_dropped`
- Replaced `test_slice_refresh_skips_overlay_refresh` (obsolete after direct async scheduling)

## Test commands

```bash
uv run pytest tests/cloudscope/test_primary_image_view.py::test_slice_refresh_schedules_plane_only_reload tests/cloudscope/test_primary_image_view.py::test_slice_refresh_skips_primary_x_range_reapply tests/cloudscope/test_primary_image_view.py::test_stale_slice_refresh_is_dropped tests/cloudscope/test_x_range_view_wiring.py -q
uv run pytest tests/cloudscope/test_primary_image_view.py -q
```

## Test results

```
uv run pytest tests/cloudscope/test_primary_image_view.py -q  → 23 passed
uv run pytest (127 focused + x_range wiring)                  → 18 passed
```

## GUI verification (user)

Run 8-step recipe from chat on `threed-examples` / `20190320_b_.oir`.

## Follow-ups

- Ticket 128: atomic Z/T plane swap (single browser paint, preserve full 2D viewport)
- Ticket 129: atomic channel swap
