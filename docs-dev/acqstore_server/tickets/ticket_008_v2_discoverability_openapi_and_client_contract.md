# Ticket 008 — API v2 discoverability, OpenAPI, and client contract

## Scope

Improve API v2 usability for browser clients, Python clients, and LLM-generated clients without adding acquisition-specific semantics.

## Read-only AcqStore API inspection

No new AcqStore API calls were introduced in this ticket. `src/acqstore/` was not edited.

## Implementation

- Added `GET /api/v2` as a discoverable API entry point.
- Added stable links to health, capabilities, open, pick-and-open, OpenAPI, Swagger UI, and the maintained v2 demo.
- Added operation summaries and descriptions to the v2 routes.
- Described binary responses in OpenAPI as `application/octet-stream` with binary string schemas.
- Added concrete request examples for `OpenRequest` and `PickAndOpenRequest`.
- Added a behavioral client-contract test covering capabilities, open, channel download, float32 decoding, reshaping, session inspection, and explicit deletion.

## Contract principles

- JSON uses camelCase only at the public schema layer.
- Internal models remain free of URLs and JSON naming concerns.
- Channel indices are generic and carry no calcium/vessel roles.
- Binary arrays are row-major little-endian float32.
- Clients use the reported shape rather than infer dimensions.
- Reference coordinates remain in AcqStore semantics; no Plotly transpose is encoded by the server.

## Validation

Run:

```bash
uv run pytest tests/acqstore_server
uv run ruff check src/acqstore_server tests/acqstore_server
```

## Files

- `src/acqstore_server/v2/routes.py`
- `src/acqstore_server/v2/schemas.py`
- `tests/acqstore_server/v2/test_client_contract.py`
- `tests/acqstore_server/v2/test_openapi.py`
- `docs-dev/acqstore_server/v2/api.md`
- `docs-dev/acqstore_server/v2/README.md`
