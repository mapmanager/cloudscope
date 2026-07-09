# 008 Strict OME-Zarr round-trip report

## Files changed

- `src/acqstore/acq_image/acq_image.py`
- `src/acqstore/acq_image/ome_zarr_io.py`
- `src/acqstore/acq_image/tiff_export.py`
- `tests/acqstore/test_ome_zarr_file_loader.py`
- `tests/acqstore/test_ome_zarr_io.py`
- `tests/acqstore/test_tiff_export.py`
- `tests/acqstore/ome_zarr/conftest.py`
- `tests/acqstore/ome_zarr/test_native_cs_ome_zarr_round_trip.py`
- `tests/acqstore/ome_zarr/test_ome_zarr_round_trip.py`
- `tests/acqstore/ome_zarr/test_tiff_export_imagej_metadata.py`

## Summary of implementation

- Made OME-Zarr reads fail fast when required OME-NGFF `multiscales`, `axes`, `datasets`, dataset `path`, or level-0 `scale` metadata are missing or malformed.
- Added support for reading BioIO OME-Zarr v3 / NGFF 0.5 metadata from the root `ome` attribute while keeping v2 / NGFF 0.4 root `multiscales` support.
- Removed silent physical-calibration fallbacks from OME-Zarr read/write code. Invalid or incomplete calibration now raises clear `ValueError` exceptions.
- Made native `.cs.ome.zarr` header parsing strict. Required acqstore header fields must be present and consistent because acqstore owns both the writer and reader for native stores.
- Made native `.cs.ome.zarr` sidecar loading fail fast when the embedded sidecar is missing or malformed.
- Fixed TIFF ImageJ metadata export so an `Info` note always records acqstore axis calibration.
- TIFF export now writes real ImageJ X/Y resolution and unit metadata only when X and Y share a single physical unit, avoiding misleading calibration for kymographs such as `Y=seconds`, `X=micrometer`.
- Moved OME-Zarr/TIFF persistence tests into `tests/acqstore/ome_zarr/`. The prior root-level test modules are now empty relocation stubs so existing files do not continue running duplicate/obsolete assertions.

## Tests added or modified

- Added calibrated `AcqPixels` fixtures for deterministic OME-Zarr round-trip tests independent of vendor file loaders.
- Added pure `.ome.zarr` round-trip tests for mixed-axis and shared-spatial physical units.
- Added Zarr v2 / NGFF 0.4 calibration round-trip coverage.
- Added native `.cs.ome.zarr` strict header round-trip and malformed-header tests.
- Added TIFF ImageJ metadata tests for mixed kymograph units and shared spatial units.
- Updated old root-level OME-Zarr/TIFF test files to relocation stubs.

## Exact test commands run

```bash
uv run pytest tests/acqstore/ome_zarr -q
uv run pytest tests/acqstore/ome_zarr tests/acqstore/test_ome_zarr_io.py tests/acqstore/test_ome_zarr_file_loader.py tests/acqstore/test_tiff_export.py -q
uv run pytest tests/acqstore -q
```

## Test results

- `uv run pytest tests/acqstore/ome_zarr -q`: `9 passed in 0.53s`.
- `uv run pytest tests/acqstore/ome_zarr tests/acqstore/test_ome_zarr_io.py tests/acqstore/test_ome_zarr_file_loader.py tests/acqstore/test_tiff_export.py -q`: `9 passed in 0.40s`.
- `uv run pytest tests/acqstore -q`: `484 passed, 10 skipped, 12 warnings in 20.81s`.

## Concerns or follow-ups

- Full repository pytest was not run for this hotfix pass; focused acqstore tests passed.
- The new tests validate local OME-Zarr and native CS OME-Zarr round trips. Live AWS `s3://` access still needs manual validation against a development bucket.
- The relocation-stub root test files can be deleted in a normal git workflow. Replacement zips cannot delete files, so they are overwritten as no-op modules here.
