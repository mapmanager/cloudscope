# Ticket 007: Fix primary image selection orchestration

## Files changed

- `src/cloudscope/controllers/image_pixels_controller.py` — rewritten around `ensure_loaded(..., on_complete=...)`; removed `bind()`, event-bus subscription, and `ImagePixelsReady` publishing
- `src/cloudscope/controllers/home_page_controller.py` — accepts `image_pixels_controller`; defers `FileSelectionChanged` until pixels load (immediate on clear)
- `src/cloudscope/runtime.py` — wires `ImagePixelsController` into `HomePageController`; removed `image_pixels_controller.bind()`
- `src/cloudscope/views/primary_image_view.py` — restores `on_primary_selection_changed` refresh; removes pixel/channel event subscriptions; idle `clear_data()` + label instead of black placeholder
- `src/cloudscope/events/image_pixels.py` — deleted (`ImagePixelsReady` removed)
- `tests/cloudscope/test_image_pixels_controller.py` — tests `ensure_loaded` callbacks
- `tests/cloudscope/test_primary_image_pixels_wiring.py` — tests selection-driven refresh
- `tests/cloudscope/test_primary_image_view_handlers.py` — restores `on_primary_selection_changed` refresh test
- `tests/cloudscope/test_primary_image_view.py` — updates no-selection / clear-display tests
- `tests/cloudscope/test_home_page_pixels_orchestration.py` — new integration tests for deferred `FileSelectionChanged`

## Summary of implementation

Fixed the GUI regression from ticket 006 where synchronous `ImagePixelsReady` fired before `BaseView` updated `current_selection`, causing the primary raster to skip refresh.

Orchestration is now:

1. `HomePageController` updates internal selection.
2. `ImagePixelsController.ensure_loaded` runs (hot path: immediate callback; cold path: `run.io_bound(load_image_data)` with stale-generation guard).
3. `on_complete` publishes `FileSelectionChanged` once.
4. `PrimaryImageView.on_primary_selection_changed` slices and displays via `get_slice_data_loaded`.

Clear selection (`file_id=None`) still publishes `FileSelectionChanged` immediately. During cold loads the previous image stays on screen until the new selection event. Idle and error states use `clear_data()` with a “No file selected” label instead of a fake 2×2 black heatmap.

## Tests added or modified

- Added `tests/cloudscope/test_home_page_pixels_orchestration.py`
- Rewrote `tests/cloudscope/test_image_pixels_controller.py`
- Rewrote `tests/cloudscope/test_primary_image_pixels_wiring.py`
- Updated `tests/cloudscope/test_primary_image_view_handlers.py`
- Updated `tests/cloudscope/test_primary_image_view.py`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_image_pixels_controller.py tests/cloudscope/test_primary_image_pixels_wiring.py tests/cloudscope/test_primary_image_view_handlers.py tests/cloudscope/test_primary_image_view.py tests/cloudscope/test_home_page_pixels_orchestration.py tests/cloudscope/test_controller.py -q

uv run pytest -q
```

## Test results

- Focused tests: **45 passed**
- Full suite: **1244 passed**, 15 warnings

## Concerns or follow-ups

- Loading spinner during cold pixel loads deferred to a later ticket.
- Lazy `AcqImage.__init__` (folder load without full pixel read for CZI/OIR/TIF) deferred to a later ticket.
- OME-Zarr cold-load UX (previous image kept on screen) is acceptable for now per plan.
