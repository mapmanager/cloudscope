# Ticket 127d — Z slider dead after file switch + zoom

## Files changed

- `src/cloudscope/views/primary_image_view.py`
- `tests/cloudscope/test_primary_image_view.py`
- `.cursor/rules/plotly-callback-edits.mdc`

## Summary

User repro: file switch → scroll zoom (heatmap OK) → Z scrub → **slider thumb
does not move**, no Path B logs.

Hypothesis: Quasar ``QSlider`` ``min``/``max`` in the browser drift from Python
``_props`` after ``Plotly.react`` / full figure rebuilds. File-switch-only scrub
worked; zoom-then-scrub failed.

Fixes:

1. ``_configure_nicegui_slider_bounds`` — batch ``min``/``max`` with
   ``suspend_updates()``, cast to ``int``, call ``slider.update()`` explicitly.
2. ``_sync_slice_sliders_from_header()`` after every successful raster refresh
   (Path A and Path B).
3. ``_sync_slice_sliders_from_header()`` after user zoom
   (``_on_viewer_x_range_changed`` with finite x range).
4. DEBUG on Z slider handler (fired vs suppressed).

Added workspace rule: **must disclose Plotly callback edits prominently** (see
``.cursor/rules/plotly-callback-edits.mdc``).

**No Plotly callback logic changed in this ticket.**

## Tests

- ``test_configure_nicegui_slider_bounds_updates_props_not_python_attrs`` — asserts
  ``update()`` called.

## Commands

```bash
uv run pytest tests/cloudscope/test_primary_image_view.py -q
```

## Results

See pytest output in session.

## Retest recipe

```
1. threed-examples → file 1
2. Switch to 20190401__0002.oir (Z=28)
3. Scroll-zoom → heatmap_z logs
4. Scrub Z → thumb moves + Path B logs
5. Report pass/fail
```

## Follow-ups

- Z scrub still resets zoom until ticket **128**.
- Revert anchor remains ``399b2f2b`` if behavior stays non-deterministic.
