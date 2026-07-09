# 007 Acqstore OME-Zarr, AWS, and TIFF export report

## Files changed

- `pyproject.toml`
- `uv.lock`
- `scripts/acqstore/try_ome_zarr.py`
- `src/acqstore/acq_image/acq_analysis_set.py`
- `src/acqstore/acq_image/acq_image.py`
- `src/acqstore/acq_image/acq_pixels.py`
- `src/acqstore/acq_image/aws_zarr_recipe.md`
- `src/acqstore/acq_image/file_loaders/loader_registry.py`
- `src/acqstore/acq_image/ome_zarr_io.py`
- `src/acqstore/acq_image/supported_import_extensions.py`
- `src/acqstore/acq_image/tiff_export.py`
- `src/acqstore/acq_image/zarr_store_utils.py`
- `tests/acqstore/test_ome_zarr_file_loader.py`
- `tests/acqstore/test_ome_zarr_io.py`
- `tests/acqstore/test_supported_import_extensions.py`
- `tests/acqstore/test_tiff_export.py`

## Summary of implementation

- Added TIFF export through `AcqImage.save_as_tif(...)`, backed by `tifffile`, with full-array export and optional ImageJ/Fiji metadata hints for physical scale and time spacing.
- Switched new OME-Zarr export path to use `bioio-ome-zarr` behind `AcqPixels` / `AcqImage` APIs instead of building new export behavior directly on `ome-zarr-py`.
- Defaulted new OME-Zarr exports to Zarr v3 / OME-NGFF 0.5, with `zarr_format=2` available for Zarr v2 / OME-NGFF 0.4.
- Added required multiscale shape declaration for OME-Zarr exports, downsampling Y/X by powers of two when images are large enough for additional levels.
- Added pure OME-Zarr export through `AcqImage.save_as_ome_zarr(...)` with no acqstore sidecars.
- Extended native CloudScope/acqstore export through `AcqImage.save_native_zarr(...)` with acqstore sidecars and analysis tables.
- Added local ZIP snapshot support for `.ome.zarr.zip` and `.cs.ome.zarr.zip` exports and reads.
- Added S3-aware path helpers and sidecar JSON/CSV helpers for `s3://` native stores.
- Added registered loader support for `.ome.zarr.zip` and `.cs.ome.zarr.zip`.
- Rewrote `scripts/acqstore/try_ome_zarr.py` as a documented hard-coded development exercise script covering TIFF, pure OME-Zarr, native CS OME-Zarr, ZIP snapshots, and reload summaries.
- Added `src/acqstore/acq_image/aws_zarr_recipe.md` with AWS CLI setup, sync examples, and direct `s3://` acqstore target examples.

## Tests added or modified

- Added `tests/acqstore/test_tiff_export.py`.
- Updated OME-Zarr tests for BioIO-backed writer dependency and NGFF 0.5 default metadata.
- Updated supported-extension tests for `.ome.zarr.zip` and `.cs.ome.zarr.zip`.

## Exact test commands run

```bash
uv lock
uv run python -m py_compile src/acqstore/acq_image/acq_image.py src/acqstore/acq_image/acq_pixels.py src/acqstore/acq_image/acq_analysis_set.py src/acqstore/acq_image/ome_zarr_io.py src/acqstore/acq_image/tiff_export.py src/acqstore/acq_image/zarr_store_utils.py scripts/acqstore/try_ome_zarr.py
uv run pytest tests/acqstore/test_tiff_export.py tests/acqstore/test_supported_import_extensions.py tests/acqstore/test_native_zarr_discovery.py tests/acqstore/test_ome_zarr_io.py tests/acqstore/test_ome_zarr_file_loader.py
uv run pytest
```

## Test results

- `uv lock`: completed successfully.
- `uv run python -m py_compile ...`: completed successfully.
- Focused pytest command: `23 passed in 5.36s`.
- Full pytest command: `1828 passed, 15 skipped, 15 warnings in 27.00s`.

## Concerns or follow-ups

- Direct real AWS `s3://` write/read was not exercised against a live bucket in pytest. The implementation includes S3-aware helpers and depends on `s3fs`, but live AWS validation should be done with a development bucket using `scripts/acqstore/try_ome_zarr.py` or a dedicated future integration script.
- S3 overwrite cleanup is intentionally fail-fast rather than recursively deleting prefixes from acqstore. For now, remove S3 prefixes with AWS CLI before overwriting remote stores.
- TIFF export is intentionally standard `tifffile.imwrite` output, not OME-TIFF or explicit BigTIFF. Very large exports may require a future option if standard TIFF limits are encountered.
- ZIP-backed Zarr support is for immutable local snapshots, not S3-hosted ZIP mutation.
