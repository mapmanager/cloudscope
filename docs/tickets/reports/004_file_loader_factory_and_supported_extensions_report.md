# Ticket Report: 004 File Loader Factory and Supported Extensions

## Files Changed

- `src/acqstore/acq_image/supported_import_extensions.py` (new)
- `src/acqstore/acq_image/file_loaders/file_loader_factory.py` (new)
- `src/acqstore/acq_image/acq_image.py`
- `src/acqstore/acq_image/acq_image_list.py`
- `tests/acqstore/test_file_loader_factory.py` (new)
- `tests/acqstore/test_acq_image_list.py`
- `docs/acqstore/schemas.md`
- `docs/tickets/reports/004_file_loader_factory_and_supported_extensions_report.md`

## Summary of Implementation

- Added `supported_import_extensions.py` as the single source of truth for `AllowedImportExtension` and `ALLOWED_IMPORT_EXTENSIONS` (`tif`, `oir`, `czi` only).
- Added `create_file_loader(path)` factory: validates suffix against `ALLOWED_IMPORT_EXTENSIONS` (case-insensitive), rejects `.tiff`, dispatches to `TiffFileLoader` (with `load_olympus_header=True`), `OirFileLoader`, or `CziFileLoader`.
- Wired `AcqImage` to use the factory instead of instantiating abstract `BaseFileLoader`; re-exported extension names from `acq_image.py` via `__all__`.
- Updated `AcqImageList` to import `ALLOWED_IMPORT_EXTENSIONS` from `supported_import_extensions` (includes `czi`; walk remains case-insensitive on suffix).
- Documented supported formats in `docs/acqstore/schemas.md`.
- Did not modify `scripts/acqstore/*` (per request).

## Tests Added or Modified

- New `tests/acqstore/test_file_loader_factory.py`
- Updated `tests/acqstore/test_acq_image_list.py`

## Exact Test Commands Run

- `uv run pytest`

## Test Results

- `66 passed` using `uv run pytest`.

## Concerns or Follow-ups

- OIR/CZI loader construction still requires valid files (header read in `__init__`); integration tests with real fixtures can be added later.
- Scripts under `scripts/acqstore/` may still duplicate extension lists until updated manually.
