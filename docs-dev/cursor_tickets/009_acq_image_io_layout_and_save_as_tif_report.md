# 009 AcqImage IO layout and Save As Tif report

## Files changed

- `src/acqstore/acq_image/io/__init__.py` (new, empty)
- `src/acqstore/acq_image/io/tiff.py` (moved from `tiff_export.py`)
- `src/acqstore/acq_image/io/ome_zarr.py` (moved from `ome_zarr_io.py`)
- `src/acqstore/acq_image/io/store_utils.py` (moved from `zarr_store_utils.py`)
- `docs-dev/acqstore/ome_zarr/aws_zarr_recipe.md` (moved from `src/acqstore/acq_image/`)
- `src/acqstore/acq_image/acq_image.py`
- `src/acqstore/acq_image/acq_pixels.py`
- `src/acqstore/acq_image/file_loaders/ome_zarr_file_loader.py`
- `src/cloudscope/events/files.py`
- `src/cloudscope/controllers/load_save_controller.py`
- `src/cloudscope/views/file_list_tree_view.py`
- `tests/acqstore/test_io_package_imports.py` (new)
- `tests/acqstore/test_tiff_export.py`
- `tests/acqstore/ome_zarr/test_tiff_export_imagej_metadata.py`
- `tests/acqstore/ome_zarr/test_ome_zarr_round_trip.py`
- `tests/acqstore/ome_zarr/test_native_cs_ome_zarr_round_trip.py`
- `tests/cloudscope/test_load_save_controller.py`
- `tests/cloudscope/test_file_list_tree_view.py`

## Summary of implementation

### Backend layout

- Grouped TIFF / OME-Zarr / store helpers under `acqstore.acq_image.io`.
- Kept public `AcqImage` APIs unchanged: `save_as_tif`, `save_as_ome_zarr`, `save_native_zarr`.
- Moved AWS developer recipe out of `src/` into `docs-dev/acqstore/ome_zarr/`.
- Updated all production and test imports to the new module paths.

### Save As Tif... GUI

- Added tree context menu item **Save As Tif...** on `AcqImageListTreeView`.
- Added `SaveAsTifIntent` and handled it in existing `LoadSaveController` (no new ExportController).
- **Native desktop:** OS save dialog via `_prompt_for_save_path`, then `await run.io_bound(save_as_tif, ...)`.
- **Web/server (`CLOUDSCOPE_NATIVE=0`):** temp TIFF via `run.io_bound`, then `ui.download` (client `safe_invoke` when available).
- **No TaskRunner / modal progress dialog** for Save As Tif (avoids empty NiceGUI slot after OS dialog await, which left the modal stuck open after a successful write).
- Footer status stages: `Saving tif...` then `Tif saved` (FooterView remarsals via `safe_invoke` when slot is empty).

## Tests added or modified

- Added `tests/acqstore/test_io_package_imports.py` for new import paths.
- Updated OME-Zarr/TIFF tests to import from `acqstore.acq_image.io.*`.
- Added/updated LoadSaveController tests for web download, native dialog path, cancel, missing file, and two-stage footer status without TaskRunner.
- Added tree-view tests that Save As Tif publishes `SaveAsTifIntent` / warns on empty selection.

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_io_package_imports.py tests/acqstore/test_tiff_export.py tests/acqstore/ome_zarr tests/cloudscope/test_load_save_controller.py tests/cloudscope/test_file_list_tree_view.py -q
uv run pytest tests/acqstore tests/cloudscope/test_load_save_controller.py tests/cloudscope/test_file_list_tree_view.py -q
uv run pytest tests/cloudscope/test_load_save_controller.py -q -k 'save_as_tif or suggested_tif'
```

## Test results

- Initial focused command: `74 passed in 0.62s`.
- Broader command: `559 passed, 12 warnings in 5.00s`.
- Post-fix Save As Tif tests: `5 passed, 31 deselected in 1.24s`.

## Style cleanup (follow-on)

- Typed Save As / Save Selected helpers as ``AcqImage`` instead of ``object``.
- Replaced constant-string ``getattr(acq_file, 'save_as_tif')`` with ``acq_file.save_as_tif``.
- Replaced path/file_id duck-typing with ``acq_file.path`` / ``acq_file.file_id``.
- Dropped ``hasattr(client, 'safe_invoke')``; call ``client.safe_invoke`` when client is not None.
- Left NiceGUI ``getattr(app, 'native', ...)`` alone.

## Concerns or follow-ups

- Full-repo `uv run pytest` was not run in this pass; focused acqstore + Save As coverage passed.
- Web download uses a temporary server-side file only as a staging buffer for `ui.download`; cleanup of that temp directory is left to OS temp cleanup (NiceGUI `single_use` static file). Manual webserver verification of download + footer stages is still recommended.
- Save As OME-Zarr / CS OME-Zarr menu items remain out of scope.
- Native overwrite uses `overwrite=True` after the user explicitly chose a save path in the OS dialog.
- Separate next ticket: Save Selected button stays disabled after Experimental Metadata edits — addressed in `010_save_selected_dirty_refresh_report.md`.
- Separate UX bug: right-click on unloaded tree row before single-click lazy load.
