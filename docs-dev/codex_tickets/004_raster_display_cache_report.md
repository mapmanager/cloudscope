# Ticket 004 — Raster display LRU cache

## Files changed

- `src/cloudscope/raster_display_cache.py` (new)
- `src/cloudscope/runtime.py`
- `src/cloudscope/pages/home_page.py`
- `src/cloudscope/views/primary_image_view.py`
- `src/cloudscope/views/reference_image_view.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
- `scripts/dev/profile_raster_switch.py` (new)
- `tests/cloudscope/test_raster_display_cache.py` (new)
- `tests/cloudscope/test_primary_image_view.py`
- `tests/nicewidgets/test_plotly_raster_viewer.py`

## Summary of implementation

Added a process-local **`RasterDisplayCache`** in CloudScope with configurable LRU capacity (default **3**, override via `CLOUDSCOPE_RASTER_DISPLAY_CACHE_MAX_ENTRIES`).

Cache key: `(file_id, channel, plane_kind)` where `plane_kind` is `primary` or `reference`.

On miss, the cache loads the 2D plane via a caller-supplied loader and builds **`ImagePyramid`** once. On hit, plane + pyramid are reused.

**Physical calibration does not require pyramid rebuild.** `ImagePyramid` downsamples raw pixel arrays only (`pyramid.py`). Grid/`RasterGridSpec` is refreshed from the current header on each display and passed into a new `RasterViewService` via **`PlotlyRasterViewer.set_data_from_pyramid()`**.

`PrimaryImageView` and `ReferenceImageView` receive the shared runtime cache from `home_page.py`. Primary view subscribes to **`MetadataChanged`** for `acq_image_header` and re-displays with updated grid while reusing the cached pyramid.

## Tests added or modified

- `tests/cloudscope/test_raster_display_cache.py` — LRU, env override, primary/reference key separation, payload helper
- `tests/nicewidgets/test_plotly_raster_viewer.py` — `set_data_from_pyramid`
- `tests/cloudscope/test_primary_image_view.py` — updated mock for `_load_primary_display_payload`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_raster_display_cache.py -q
uv run pytest tests/cloudscope/test_primary_image_view.py::test_publishes_primary_plane_loaded_after_set_data -q
uv run pytest -q
uv run python scripts/dev/profile_raster_switch.py
```

## Test results

- `test_raster_display_cache.py`: **8 passed**
- `test_publishes_primary_plane_loaded_after_set_data`: **1 passed**
- Full suite: **1226 passed**, 15 warnings

## Phase 0 profiling (user CZI paths)

Script: `scripts/dev/profile_raster_switch.py`

Example output on Image 10 / Image 17:

| Step | Time |
|------|------|
| Cold pyramid build (10) `(10000, 1024)` | ~15 ms |
| Cold pyramid build (17) `(50000, 1024)` | ~90 ms |
| Cached revisit (pass 2+) | ~0 ms |

LRU held 2 entries with default max 3.

## Concerns or follow-ups

- **LRU cap:** Document/set `CLOUDSCOPE_RASTER_DISPLAY_CACHE_MAX_ENTRIES=2` (or `3`) on memory-constrained cloud hosts.
- **Reference plane load:** Reference view still resolves the plane from AcqStore on each refresh before cache lookup; pyramid reuse is the main win today.
- **File reload:** Cache is not cleared when `AcqImageList` is replaced; add invalidation if in-memory pixel reload becomes a workflow.
- **Grid fingerprint in cache key:** Not needed for pyramid correctness; grid is always taken from current header/plane at display time.
