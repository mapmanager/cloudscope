# 040 — Crisp reference overview (Approach B)

## Summary

The reference image's full-extent overview PNG looked blurry and low-contrast
compared to the crisp zoomed-in heatmap, even though both used the same
percentile contrast window (ticket 039). Root cause: `full_image_png` always
selected a conservative coarse pyramid level (`min(num_levels - 1, 3)`), so a
small reference image (e.g. 512x512) was shown as a heavily box-averaged
thumbnail (e.g. level 3 = 8x downsample = 64x64) stretched to fill the plot.
Box averaging both blurs the image and compresses its dynamic range, so a
window computed from the full-resolution plane looks dim on the averaged
overview.

Approach B keeps the overview as a PNG but lets callers pass a pixel budget so
small images render the full extent at full (or finest fitting) pyramid
resolution. The reference view opts in with a 4,000,000 px budget. The primary
image path is unchanged (no budget passed -> existing coarse overview).

## Files changed

- `src/nicewidgets/raster_viewer/backend/raster_service.py`
  - `full_image_png(..., max_pixels: int | None = None)`: new optional budget.
  - New `_overview_level(max_pixels)` helper: returns the finest pyramid level
    whose array size fits the budget; coarsest level when none fit; the
    existing `min(num_levels - 1, 3)` when `max_pixels is None`.
- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
  - New `_overview_max_pixels` instance state.
  - `set_data(..., overview_max_pixels: int | None = None)`: stores the budget.
  - Forwards `max_pixels=self._overview_max_pixels` to all `full_image_png`
    call sites: `set_data`, `_on_plotly_doubleclick` (reset), `_refresh_full_png`,
    and `_build_initial_figure`. So both initial render and double-click reset
    stay crisp.
- `src/cloudscope/views/reference_image_view.py`
  - New `_REFERENCE_OVERVIEW_MAX_PIXELS = 4_000_000` constant.
  - `set_data(..., overview_max_pixels=_REFERENCE_OVERVIEW_MAX_PIXELS)`.

## Design notes

- `max_pixels is None` preserves prior behavior exactly, so the primary
  kymograph viewer and any other consumer are unaffected.
- `level_info()` is ordered finest (level 0) to coarsest; the first level under
  budget is the finest acceptable overview.
- Approach B chosen over Approach A (render full extent as a heatmap) because B
  is surgical, keeps `set_data` viewport-free, and a full-resolution grayscale
  PNG is visually indistinguishable from the heatmap for scientific images.

## Tests added or modified

- `src/nicewidgets/raster_viewer/tests/backend/test_raster_service.py`
  - `test_full_image_png_default_uses_coarse_overview`
  - `test_full_image_png_max_pixels_selects_finest_fitting_level`
  - `test_full_image_png_max_pixels_steps_to_coarser_level`
  - `test_full_image_png_max_pixels_too_small_uses_coarsest_level`
  - `test_full_image_png_explicit_level_overrides_max_pixels`

## Test commands run

```bash
uv run pytest src/nicewidgets/raster_viewer/tests/backend/test_raster_service.py tests/cloudscope/test_reference_image_view.py -q
uv run pytest src/nicewidgets/raster_viewer/tests -q
```

## Test results

```
......................                                                   [100%]
22 passed in 1.05s

..........................................                               [100%]
42 passed in 0.46s
```

## Concerns / follow-ups

- 4,000,000 px budget is a CloudScope policy choice (covers 512^2 and 2048^2 at
  full res). Very large reference images still step to a coarser overview.
- Deferred (kept in memory for future work): Ticket 041 — Heatmap integer dtype
  passthrough (stop casting integer clips to float32 in `render`, ship
  uint8/uint16 to Plotly; float32 only for float/NaN sources). Not implemented
  here.
