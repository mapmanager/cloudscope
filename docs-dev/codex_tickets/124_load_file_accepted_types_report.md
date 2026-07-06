# 124 Load File Accepted Types Report

## Files Changed

- `src/acqstore/acq_image/file_loaders/loader_registry.py`
- `src/acqstore/acq_image/file_loaders/file_loader_factory.py`
- `src/acqstore/acq_image/supported_import_extensions.py`
- `src/acqstore/acq_image/acq_image.py`
- `src/acqstore/upload_store.py`
- `src/cloudscope/_py_web_view.py`
- `src/cloudscope/views/load_save_view.py`
- `tests/acqstore/test_supported_import_extensions.py`
- `tests/acqstore/test_upload_store.py`
- `tests/cloudscope/test_py_web_view.py`
- `tests/cloudscope/test_load_save_view.py`

## Summary Of Implementation

- Added a loader registry for AcqImage file loaders and exposed loader-backed supported import extensions.
- Kept runtime allowed import extensions as a validated subset of registered loader extensions, preventing callers from advertising extensions with no loader.
- Updated the native pywebview open-file dialog helper to support one file filter with multiple extensions.
- Wired the `Load File` native picker to the acqstore acquisition extension set instead of hard-coded `.tif`.
- Kept CSV manifest loading on its separate `.csv` filter.
- Updated upload filename validation to use acqstore compound suffix normalization so `.ome.zarr` and `.cs.ome.zarr` align with advertised accepted extensions.

## Tests Added Or Modified

- Added acqstore tests for the loader-backed supported extension API and rejection of unregistered extensions.
- Added pywebview tests for multi-extension file filter formatting.
- Added LoadSaveView tests proving `Load File` passes all acquisition extensions and `Load CSV` still passes `.csv`.
- Extended upload-store tests to accept `.ome.zarr` and `.cs.ome.zarr` filenames.

## Exact Test Commands Run

```bash
uv run pytest tests/acqstore/test_supported_import_extensions.py tests/acqstore/test_upload_store.py tests/cloudscope/test_py_web_view.py tests/cloudscope/test_load_save_view.py
```

## Test Results

- `72 passed in 0.83s`
- `ReadLints` found no linter errors in edited files.

## Concerns Or Follow-Ups

- `.ome.tif` is not currently registered as an acqstore `AcqImage` loader extension and was left out of scope.
- This change updates the native picker filter construction but does not browser-verify the macOS dialog UI, because the behavior is covered through the pywebview `file_types` parameter passed to `create_file_dialog`.
