# 002 — Pyramid coverage fix (choose_level + MIN_PYRAMID_AXIS)

## Files changed

- `src/nicewidgets/raster_viewer/backend/pyramid.py` — `MIN_PYRAMID_AXIS = 6`; stop building when next level short side would fall below 6
- `src/nicewidgets/raster_viewer/backend/raster_service.py` — `_level_covers_bounds()`; `choose_level()` refines to finer levels when clip would truncate bounds
- `tests/nicewidgets/test_raster_service.py` — kymograph regression, square smoke, partial spatial zoom tests
- `src/nicewidgets/raster_viewer/tests/backend/test_pyramid.py` — min-axis cap tests; updated level expectations
- `src/nicewidgets/raster_viewer/tests/backend/test_image_model.py` — fixture shape updates
- `src/nicewidgets/raster_viewer/tests/conftest.py` — sample array `(16, 32)` so pyramid fixture still builds multiple levels under the cap

## Summary of implementation

**Part A — `choose_level` coverage refinement**

After the existing density-based level pick, walk to finer pyramid levels while `_level_covers_bounds()` reports truncation. Coverage uses the same `ceil(row/col_max / ds) <= arr.shape` math as `clip_from_level`, so a selected level always tiles the visible bounds on both axes. Fixes the top-y heatmap misalignment when time density picked `ds=16` on a 24-column kymograph (one spatial pyramid bin covering cols 0–15 only).

**Part B — `MIN_PYRAMID_AXIS = 6`**

`ImagePyramid._build()` no longer appends a level when the next 2× downsample would yield `min(height, width) < 6`. For `(30000, 24)` kymographs the coarsest level is `(7500, 6)` at `ds=4` instead of `(1875, 1)` at `ds=16`. Square `(1024, 1024)` images use the same rule; coarsest level is `(8, 8)` at `ds=128`. No separate code path for kymograph vs square.

`render()` debug `logger.info` lines were left unchanged.

## Tests added or modified

**Added**

- `test_choose_level_refines_when_spatial_axis_truncated`
- `test_choose_level_allows_coarser_level_for_partial_spatial_extent`
- `test_render_spatial_extent_covers_full_col_bounds`
- `test_render_square_image_full_bounds_coverage`
- `test_pyramid_stops_before_short_axis_collapses_below_min`
- `test_pyramid_square_image_coarsest_level_respects_min_axis`

**Modified**

- `test_pyramid_builds_expected_first_levels` — `(16, 32)` fixture, two levels under cap
- `test_clip_from_level_uses_source_coordinates` — bounds adjusted for new fixture
- `test_backend_image_shape_properties`, `test_clip_returns_requested_region`, `test_clip_clamps_to_image_extent` — fixture shape

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_raster_service.py src/nicewidgets/raster_viewer/tests/backend/test_pyramid.py -v
uv run pytest tests/nicewidgets/ src/nicewidgets/raster_viewer/tests/backend/test_pyramid.py src/nicewidgets/raster_viewer/tests/backend/test_image_model.py src/nicewidgets/raster_viewer/tests/frontend/ -q
uv run pytest
```

## Test results

- Focused raster + pyramid: **31 passed**
- Nicewidgets + raster_viewer frontend/backend (excl. duplicate `test_raster_service` module): **386 passed**
- Full `uv run pytest`: **1212 passed**

## Concerns or follow-ups

- `_overview_level()` for full-image PNG still independent; may want a follow-up so overview picks a level that also tiles full spatial extent (often already true with the cap).
- Dual-trace PNG↔heatmap flash ticket remains next.
- 1D chart ↔ primary x-range sync deferred.
