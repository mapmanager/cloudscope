# Ticket 009 — Stable API v2 error envelopes

## Goal

Make request-validation failures conform to the same stable API v2 error envelope used by service and session failures.

## Scope

Edited or added only under:

- `src/acqstore_server/`
- `tests/acqstore_server/`
- `docs-dev/acqstore_server/`

No files under `src/acqstore/` were edited. This ticket adds no new AcqStore API calls.

## API finding

Before this ticket, malformed `/api/v2` requests returned FastAPI's default top-level `detail` array even though v2 documented `ErrorResponse` for HTTP 422. This was an API inconsistency, not a broken test.

## Implementation

- Added a v2-only `StableValidationRoute`.
- Normalized `RequestValidationError` into:
  - `ok: false`
  - `error: request_validation_failed`
  - `message: Request validation failed`
  - machine-readable `details`
- Added structured validation issue schemas.
- Kept v1 validation behavior unchanged.
- Ensured ordinary service errors omit `details` rather than returning `null`.

## Validation coverage

Tests cover:

- missing request fields;
- schema validators and forbidden extra fields;
- malformed JSON;
- invalid path parameters;
- unchanged v1 validation behavior;
- OpenAPI schema references.

## Files

### Added

- `src/acqstore_server/v2/errors.py`
- `tests/acqstore_server/v2/test_errors.py`
- `docs-dev/acqstore_server/v2/errors.md`
- `docs-dev/acqstore_server/tickets/ticket_009_stable_v2_error_envelopes.md`

### Edited

- `src/acqstore_server/v2/routes.py`
- `src/acqstore_server/v2/schemas.py`
- `tests/acqstore_server/v2/test_openapi.py`

## Next actions

- Add optional representative-file integration tests for TIFF, OIR, CZI, and ND2.
- Keep those tests disabled or skipped when local fixture paths are unavailable.
- Continue using the maintained v2 browser demo as a behavioral client contract.
