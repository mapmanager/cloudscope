# 125 Primary image Z/T slicing

## Files changed

- `src/cloudscope/views/primary_image_view.py`
- `src/cloudscope/views/image_toolbar_view.py`
- `src/cloudscope/views/reference_image_view.py`
- `src/cloudscope/raster_display_cache.py`
- `src/cloudscope/events/raster.py`
- `src/cloudscope/events/contrast.py`
- `src/cloudscope/contrast_seeding.py`
- `src/nicewidgets/contrast_widget/intent.py`
- `src/nicewidgets/contrast_widget/contrast_widget.py`
- `tests/cloudscope/test_primary_image_view.py`
- `tests/cloudscope/test_raster_display_cache.py`
- `tests/cloudscope/test_image_toolbar_view.py`
- `tests/cloudscope/test_primary_image_pixels_wiring.py`

## Summary of implementation

- `PrimaryImageView` owns view-local `_z` and `_t` (default 0). T and/or Z sliders appear below the plot when the loaded header has a multi-element `T` or `Z` axis.
- Plane loading threads `z` and `t` through `_load_primary_display_payload` → `BaseFileLoader.get_slice_data_loaded(channel, z=, t=)`.
- **Path A (selection change):** reload plane, refresh ROI + diameter overlays. File change resets `_z`/`_t` and auto-contrast mode; channel change preserves `_z`/`_t` but resets auto-contrast mode.
- **Path B (slider change):** reload plane only; skips ROI and diameter overlay refresh.
- `RasterDisplayCacheKey` extended with `z` and `t`; default LRU cap raised from 5 to 20.
- `PrimaryPlaneLoaded` extended with `z`, `t`, and `use_auto_contrast`.
- Contrast v1: ephemeral auto contrast per plane by default (no `AcqImage` write on slice navigation). Sticky manual contrast when the user edits LUT/range; Auto button reverts to auto-per-slice (`from_auto` on contrast intents).
- No changes to Plotly `.on(...)` handlers, ROI overlay construction, or `AcqImage.get_roi_image`.

## Tests added or modified

- Slice slider spec, z/t loader threading, cache key isolation
- Selection reset policy (file vs channel)
- Slice-only refresh skips overlays
- Ephemeral vs sticky toolbar seeding
- Cache key z/t separation

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_primary_image_view.py tests/cloudscope/test_raster_display_cache.py tests/cloudscope/test_image_toolbar_view.py tests/cloudscope/test_primary_image_pixels_wiring.py tests/cloudscope/test_contrast_controller.py -q
```

## Test results

50 passed in ~2s

## Concerns or follow-ups

- **Deferred:** Avoid redundant full plane reload on ROI selection change only (`on_primary_selection_changed` still reloads plane when only `roi_id` changes — pre-existing behavior).
- **v2:** Cache ephemeral auto `(min, max)` per `(file, channel, z, t)` on LRU hits to avoid recomputing histogram clip on revisits.
- Sticky manual contrast applies the same numeric window across T/Z slices; Auto reverts to per-slice auto.
- **Fix (post-v1):** NiceGUI `ui.slider` bounds must be updated via `slider._props['min']`/`['max']` and `slider.set_value()` after construction — not `.min`/`.max` attributes. Contrast controller requires one-time `AcqImage` seed per channel (`ensure_channel_contrast_from_plane` when `get_image_contrast` is `None`); display remains ephemeral via `_apply_display_contrast`.
