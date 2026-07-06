# Ticket 006 — Explicit image pixel load orchestration

## Files changed

- `src/acqstore/acq_image/acq_image.py` — `pixels_loaded()`, `load_image_data()`
- `src/acqstore/acq_image/file_loaders/base_file_loader.py` — `pixels_loaded()`, `get_slice_data_loaded()`
- `src/cloudscope/events/image_pixels.py` — new `ImagePixelsReady` state event
- `src/cloudscope/controllers/image_pixels_controller.py` — new controller
- `src/cloudscope/runtime.py` — wire `ImagePixelsController` into runtime bootstrap
- `src/cloudscope/views/primary_image_view.py` — slice-only display path; subscribe to readiness/channel events
- `tests/acqstore/test_image_pixels_api.py` — acqstore API tests
- `tests/cloudscope/test_image_pixels_controller.py` — controller tests
- `tests/cloudscope/test_primary_image_pixels_wiring.py` — primary view wiring tests
- `tests/cloudscope/test_raster_display_cache.py` — mock updated for `get_slice_data_loaded`

## Summary of implementation

Full-file pixel loads are no longer triggered implicitly from `PrimaryImageView` via `get_slice_data()`.

1. **acqstore** exposes explicit load/query APIs on `AcqImage` and `BaseFileLoader`, plus `get_slice_data_loaded()` for fail-fast slicing without disk I/O.
2. **`ImagePixelsController`** subscribes to `FileSelectionChanged` (all selection paths: tree, table, velocity pool, programmatic). On `file_id` change it runs `run.io_bound(acq_image.load_image_data)`; when pixels are already cached it publishes `ImagePixelsReady` synchronously. Same-file re-selection (e.g. pool row with different channel/ROI) also publishes readiness without reloading.
3. **`PrimaryImageView`** refreshes the raster on `ImagePixelsReady` and `ChannelSelectionChanged`, uses `get_slice_data_loaded()` in its `io_bound` display payload, and skips refresh until pixels are loaded.

Stale in-flight loads are dropped via a generation counter when the user switches files quickly.

## Tests added or modified

- Added `tests/acqstore/test_image_pixels_api.py`
- Added `tests/cloudscope/test_image_pixels_controller.py`
- Added `tests/cloudscope/test_primary_image_pixels_wiring.py`
- Modified `tests/cloudscope/test_primary_image_view_handlers.py`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_image_pixels_controller.py tests/cloudscope/test_primary_image_pixels_wiring.py tests/acqstore/test_image_pixels_api.py tests/cloudscope/test_raster_display_cache.py tests/cloudscope/test_primary_image_view.py tests/cloudscope/test_runtime.py -q
uv run pytest -q
```

## Test results

- Focused run: **50 passed**
- Full suite: **1243 passed**

## Concerns or follow-ups

- **Reference image view** still uses `get_slice_data()` (implicit load) — out of scope for this ticket.
- **Load failures** are logged but do not publish an error state event; the primary view keeps its previous/empty display.
- **PNG encode / `set_data` on event loop** remains a separate performance concern if needed later.
