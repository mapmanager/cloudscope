# 039 — Reference image PNG contrast

## Summary

The `image_png` overview rendered by `PlotlyRasterViewer` had no contrast
window applied in `ReferenceImageView`: it called `set_data()` and nothing
else, so the PNG used the raster service's default per-clip `min`/`max`
auto-stretch (unstable across pan/zoom, outlier-sensitive).

This change derives a stable percentile contrast window from the loaded
reference plane and pushes it into the viewer right after `set_data`, matching
the default-window logic already used for the primary image. It is intentionally
**not** wired to the contrast toolbar; the window is computed directly from the
plane.

Contrast for PNG mode is applied server-side (Plotly `image` traces have no
`zmin`/`zmax`), so `set_heatmap_contrast` re-encodes the overview PNG with the
window baked into the pixels. The heatmap path is unchanged.

## Files changed

- `src/cloudscope/views/reference_image_view.py`
  - New import of `contrast_clip_min_max` from `acqstore.acq_image.image_contrast`.
  - New module-level pure function `reference_contrast_window(plane)` returning
    `(zmin, zmax)` floats or `None` for empty/degenerate planes.
  - New `ReferenceImageView._apply_reference_contrast(plane)` coroutine.
  - `_refresh_reference_async` now calls `_apply_reference_contrast(plane)` after
    a successful `set_data`.
- `tests/cloudscope/test_reference_image_view.py`
  - Tests for `reference_contrast_window`: percentile window for normal data,
    `None` for empty plane, `None` for flat/placeholder plane.

## Design notes

- Reuses the existing `contrast_clip_min_max` helper (percentiles 1.0 / 99.5),
  so reference and primary images agree on the default window.
- Reuses the existing `PlotlyRasterViewer.set_heatmap_contrast()`; no new
  nicewidgets API. `nicewidgets` is untouched, respecting package boundaries.
- The placeholder `2x2` zeros plane yields `zmax <= zmin`, so the guard skips
  contrast and the viewer keeps auto-stretch.
- One extra PNG re-encode on load (auto-stretched PNG from `set_data`, then a
  windowed re-encode), matching the existing primary-image pattern.

## Tests added or modified

- `test_reference_contrast_window_uses_percentiles`
- `test_reference_contrast_window_empty_plane_returns_none`
- `test_reference_contrast_window_flat_plane_returns_none`

## Test commands run

```bash
uv run pytest tests/cloudscope/test_reference_image_view.py -q
```

## Test results

```
........                                                                 [100%]
8 passed in 1.03s
```

## Concerns / follow-ups

- `contrast_clip_min_max` returns ints. For uint8/uint16 reference data this is
  fine. A float reference image with a small dynamic range (e.g. 0–1) would
  collapse to a degenerate window and fall back to auto-stretch.
- Open discussion item (raised by user): float values from `np.percentile`
  reaching Plotly, and whether sending uint8/uint16 instead of float to the
  heatmap/PNG would be faster. Not addressed here.
