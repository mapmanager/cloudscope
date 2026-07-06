# 074 — Lazy load schema row and controller cleanup

## Files changed

### API / src
- `src/acqstore/acq_image/acq_image.py` — `get_schema_row()` builds values in schema field order
- `src/cloudscope/controllers/acq_image_data_controller.py` — removed `ensure_loaded()` compat wrapper and no-op alias
- `src/cloudscope/controllers/home_page_controller.py` — removed `image_pixels_controller` constructor alias
- `src/cloudscope/views/primary_image_view.py` — docstring references `AcqImageDataController`
- `src/cloudscope/controllers/image_pixels_controller.py` — **deleted**

### Tests
- `tests/cloudscope/test_acq_image_data_controller.py` — **added** (renamed from `test_image_pixels_controller.py`)
- `tests/cloudscope/test_image_pixels_controller.py` — **deleted**
- `tests/cloudscope/test_home_page_pixels_orchestration.py` — `is_fully_loaded` as property on fake
- `tests/acqstore/test_acq_image_tree_rows.py` — `_pixels = None`, `reference_image` on fake loader
- `tests/acqstore/test_acq_image_list.py` — fake schema row includes `loaded`, `reference_image`, `file_size`
- `tests/acqstore/test_image_pixels_api.py` — aligned with `load_pixels()` / `images_loaded` API

## Summary of implementation

1. Fixed `AcqImage.get_schema_row()` to iterate `schema.field_names()` so emitted row key order always matches `ACQ_FILE_LIST_SCHEMA`.
2. Removed the obsolete `ImagePixelsController` shim and all backward-compat aliases (`image_pixels_controller` kwarg, `ensure_loaded()` method).
3. Standardized on `AcqImageDataController.ensure_loaded_for_selection()` as the sole load entry point.
4. Updated stale test doubles to match the lazy-load API (`is_fully_loaded` property, `load_lazy_data`, `_pixels = None`, new schema fields).

## Tests added or modified

- Added: `tests/cloudscope/test_acq_image_data_controller.py`
- Modified: `test_home_page_pixels_orchestration.py`, `test_acq_image_tree_rows.py`, `test_acq_image_list.py`, `test_image_pixels_api.py`
- Deleted: `tests/cloudscope/test_image_pixels_controller.py`

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_acq_image_list.py::test_get_schema_rows_match_backend_schema \
  tests/acqstore/test_acq_image_tree_rows.py \
  tests/acqstore/test_image_pixels_api.py \
  tests/cloudscope/test_apply_metadata.py::test_apply_metadata_intent_updates_experiment_metadata_and_emits_state \
  tests/cloudscope/test_home_page_pixels_orchestration.py \
  tests/cloudscope/test_acq_image_data_controller.py

uv run pytest
```

## Test results

- Focused run: **22 passed**
- Full suite: **1244 passed**, 15 warnings

## Concerns or follow-ups

- Other test fakes (e.g. `tests/acqstore/test_analysis_pool.py::_PoolFakeAcqImage.get_schema_row`) may still omit new schema fields if those tests start validating against `ACQ_FILE_LIST_SCHEMA` strictly.
- `test_image_pixels_api.py`, `test_home_page_pixels_orchestration.py`, and `test_primary_image_pixels_wiring.py` filenames still say "pixels" but describe behavior, not the removed controller class.
