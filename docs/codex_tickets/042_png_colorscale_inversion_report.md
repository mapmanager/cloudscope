# 042 — PNG colorscale inversion vs heatmap

## Summary

The overview PNG was inverted relative to the heatmap for gray (and green/blue)
LUTs: PNG showed low intensity -> white, high -> dark, while the heatmap
correctly showed low -> dark, high -> bright.

Root cause: the heatmap trace passes a named colorscale (e.g. `Greys`) to
Plotly.js, which defines `Greys` as `[[0,black],[1,white]]`. The PNG LUT is
built in Python via `plotly.colors.sample_colorscale`, and Plotly.py resolves
`Greys`/`Greens`/`Blues` in the OPPOSITE direction (reversed vs Plotly.js).
Other scales CloudScope uses (`Reds`, `Viridis`, `Plasma`, `Hot`, `Jet`,
`Rainbow`) agree between the two. Explicit `[stop, color]` lists (e.g. the
contrast widget's `inverted_grays`) are read identically by both renderers and
were never affected.

Fix: in the PNG encoder, sample the colorscale at reversed positions
(`1 - stops`) for the known Plotly.py-reversed named scales so the encoded PNG
matches the Plotly.js heatmap. This is a single point used by both the primary
and reference image views, so both are corrected.

## Files changed

- `src/nicewidgets/raster_viewer/backend/raster_service.py`
  - New module constant `_PLOTLY_PY_REVERSED_VS_JS = {'Greys', 'Greens', 'Blues'}`.
  - `array_to_png_data_uri`: sample at `1 - stops` for those named scales;
    everything else (LUT indexing, explicit lists, agreeing names) unchanged.
- `src/nicewidgets/raster_viewer/tests/backend/test_raster_service.py`
  - `test_png_greys_matches_plotly_js_direction`
  - `test_png_explicit_inverted_grays_unaffected`

## Verification (decoded PNG endpoints, zmin=0 zmax=255, arr=[low,high])

```
Greys   low=(0,0,0)        high=(255,255,255)     # was inverted, now correct
Greens  low=(0,68,27)      high=(247,252,245)
Blues   low=(8,48,107)     high=(247,251,255)
Reds    low=(255,245,240)  high=(103,0,13)        # unchanged (already agreed)
inverted_grays low=(255,255,255) high=(0,0,0)     # explicit list, unchanged
```

## Why the encoder (not get_colorscale / DEFAULT)

- The raster viewer owns both the PNG encoder and the heatmap trace, so
  matching them is the widget's responsibility; one change fixes every consumer.
- Zero heatmap visual change and no ripple to `get_colorscale`,
  `DEFAULT_HEATMAP_COLORSCALE`, the demo `ui.select`, or the views.
- Sampling at reversed positions preserves the full multi-stop gradient, rather
  than approximating green/blue with 2-stop lists.

## Test commands run

```bash
uv run pytest src/nicewidgets/raster_viewer/tests/backend/test_raster_service.py -q
uv run pytest src/nicewidgets/raster_viewer/tests tests/cloudscope/test_reference_image_view.py -q
```

## Test results

```
16 passed in 0.06s
52 passed in 1.01s
```

## Concerns / follow-ups

- Latent, pre-existing: the contrast widget offers `Cool`, but `Cool` is not a
  Plotly.py built-in scale, so `sample_colorscale('Cool')` raises. Selecting the
  Cool LUT on a PNG-mode image would crash the encoder. Not fixed here.
- Deferred (in memory): Ticket 041 — heatmap integer dtype passthrough.
