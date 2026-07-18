# Ticket 006 — v2 capabilities, session lifecycle, and compound paths

## Scope

This slice expands the working v2 HTTP API while preserving frozen v1 production behavior.

## AcqStore source inspected

Read-only inspection was performed before implementation:

- `src/acqstore/acq_image/supported_import_extensions.py`
- `src/acqstore/acq_image/file_loaders/loader_registry.py`
- existing `AcqImage` and reference-image APIs previously documented by ticket 004

No file under `src/acqstore/` was edited.

## Implemented

- `GET /api/v2/capabilities` sourced from AcqStore's public extension functions;
- `GET /api/v2/sessions/{sessionId}` metadata;
- `DELETE /api/v2/sessions/{sessionId}` explicit cleanup;
- session byte counts, channel indices, reference indices, and remaining TTL;
- maintained demo capability display and session-delete control;
- directory-backed acquisition acceptance;
- compound OME-Zarr format normalization through AcqStore's public helper;
- architecture and format-validation documentation.

## Important correction

The previous `Path.is_file()` gate incorrectly rejected directory-backed OME-Zarr stores before AcqStore could load them. The service now checks path existence and delegates supported-path interpretation to AcqStore.

## Validation

- `uv run pytest tests/acqstore_server -q`
- `uv run ruff check src/acqstore_server tests/acqstore_server`

## Deferred

Representative OIR, CZI, ND2, and OME-Zarr acquisitions are still required for genuine format-level integration validation. Loader-registration tests are not a substitute for real files.
