# Ticket 004 — API v2 HTTP vertical slice

## Scope

Implement the first complete API v2 HTTP path while leaving the frozen v1 production modules unchanged.

## AcqStore API inspected

Before implementation, the following read-only AcqStore source was inspected:

- `src/acqstore/acq_image/acq_image.py`
- `src/acqstore/acq_image/file_loaders/base_file_loader.py`

Verified server-facing APIs include:

- `AcqImage(..., load_images=True, load_analysis_csv=False)`
- `AcqImage.pixels`
- `AcqImage.get_image_physical_units()`
- `AcqImage.images.header`
- `AcqImage.images.has_reference_image`
- `AcqImage.images.reference_image`
- pixel `num_channels` and `get_plane(c=...)`
- `ReferenceImage.num_channels`, `get_plane()`, `line_roi`, and `get_scan_path_plot()`

No files under `src/acqstore/` were edited.

## Added

- `src/acqstore_server/v2/encoding.py`
- `src/acqstore_server/v2/routes.py`
- `tests/acqstore_server/v2/test_encoding.py`
- `tests/acqstore_server/v2/test_api.py`
- `tests/acqstore_server/v2/test_openapi.py`

## Edited

- `src/acqstore_server/app.py`
- `src/acqstore_server/v2/session_store.py`

## Implemented behavior

- `GET /api/v2/health`
- `POST /api/v2/open`
- `POST /api/v2/pick-and-open`
- generic source-channel binary downloads
- generic reference-channel binary downloads
- raw contiguous row-major little-endian float32 transport encoding
- independent v2 session storage in API-only and NiceGUI-native startup paths
- typed v2 request and response models in OpenAPI
- explicit session-not-found and channel-not-found errors
- soft open/decode timeout using the existing server environment variable

## Compatibility

The existing v1 production modules were not edited:

- `src/acqstore_server/routes.py`
- `src/acqstore_server/schemas.py`
- `src/acqstore_server/open_service.py`
- `src/acqstore_server/session_store.py`

`app.py` now composes both independent APIs side by side.

## Validation

```text
uv run pytest tests/acqstore_server -q
93 passed, 1 warning

uv run ruff check src/acqstore_server tests/acqstore_server
All checks passed
```

The warning is Starlette's TestClient/httpx deprecation warning and is unrelated to this implementation.

## Next actions

- Add focused timeout/error-normalization tests for v2.
- Expand v2 API documentation with concrete JavaScript and Python clients.
- Decide whether the current static demo remains v1-only or gains a separate v2 demo.
- Test v2 against representative OIR/CZI/ND2 files after the generic TIFF contract is stable.
