# Ticket 127c — Fix viewport settle after file switch

## Files changed

- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
- `tests/nicewidgets/test_plotly_viewer_state.py`

## Summary

**Root cause:** `_on_plotly_relayout` rejected all normalized
``xaxis.range`` / ``yaxis.range`` list payloads. Scroll-wheel zoom uses that
shape. Only bracket keys (``xaxis.range[0]``) passed through. Post-``set_data``
echoes also use normalized lists — previously blocked all of them, but user zoom
after file switch often arrived as normalized lists and was silently dropped →
no ``viewport raster refresh`` logs, PNG never swapped to heatmap.

**Fix:** Replace blanket normalized rejection with
``_is_display_viewport_echo()`` — ignore only when ranges match
``_last_display_axis_ranges`` (programmatic full-extent echo). Different ranges
schedule viewport settle (scroll zoom, pan, box zoom).

Added DEBUG when relayout is filtered or browser viewport read fails.

**Not fixed here (128):** Z scrub resets zoom — Path B ``set_data_from_pyramid``
+ ``_refresh_full_png`` full figure rebuild with ``preserve_viewport=False``.

## Tests added or modified

- Renamed/replaced ``test_on_plotly_relayout_ignores_normalized_only_payload``
  → ``test_on_plotly_relayout_ignores_normalized_echo_of_last_display_viewport``
- Added ``test_on_plotly_relayout_schedules_settle_for_normalized_user_zoom``

## Test commands

```bash
uv run pytest tests/nicewidgets/test_plotly_viewer_state.py -q -k "relayout or viewport_settle"
uv run pytest tests/cloudscope/test_primary_image_view.py tests/nicewidgets/test_plotly_viewer_state.py -q
```

## Results

- Relayout/viewport subset: **19 passed**
- Full primary + viewer state: **88 passed**

## Follow-ups

- User retest: file switch → zoom → must see ``plotly_relayout: schedule`` +
  ``viewport raster refresh: mode=heatmap_z``
- Z scrub zoom reset remains until ticket **128**
