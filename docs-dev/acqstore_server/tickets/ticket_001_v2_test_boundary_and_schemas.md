# Ticket 001 — v2 test boundary, schemas, and session store

## Scope

Establish a compatibility firewall around API v1 and create the first isolated
API v2 modules.

## Changes

- Moved v1 API/open-service tests under `tests/acqstore_server/v1/`.
- Added `test_linescan_client_contract.py` for the existing line-scan HTML client.
- Added strict camelCase Pydantic API v2 schemas.
- Added generic channel-indexed API v2 session storage.
- Added focused schema and session-store tests.
- Added the initial v2 documentation index.

## Boundary

All changes are restricted to:

- `src/acqstore_server/`
- `tests/acqstore_server/`
- `docs-dev/acqstore_server/`

No API v1 production module was edited.

## Validation

- Python syntax compilation passed for the delivered files.
- Full pytest was not completed in the isolated environment because pytest was
  unavailable there.

## Files to remove after applying this replacement

These legacy test locations were moved into the `v1/` test package and should
be deleted from the working tree:

- `tests/acqstore_server/test_api_v1.py`
- `tests/acqstore_server/test_open_service.py`
