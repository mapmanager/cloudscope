# Ticket 017 — JavaScript client handoff guide

## Goal

Make API v2 usable by a senior JavaScript developer or expert LLM without requiring inspection of the Python implementation.

## Scope

- Repair the missing `HeaderResponse` import in the complete schema contract test.
- Replace the short JavaScript notes with one authoritative end-to-end client guide.
- Document both packaged-app and source-run server availability.
- Cover health, capabilities, open, native picking, binary decoding, reference images, session inspection, cleanup, and stable errors.
- Add focused documentation-contract regression tests.

## Implementation

The JavaScript guide now contains a complete reusable implementation with:

- explicit localhost API base URL;
- stable JSON error handling;
- native picker and server-path opening;
- portable little-endian float32 decoding using `DataView`;
- byte-length and sample-count validation;
- explicit client-side transpose immediately before display;
- source and reference plane handling;
- session metadata and deletion;
- CORS, relative URL, and TTL guidance.

The API reference links to this guide and no longer uses biological-role wording.

## Validation

Run:

```bash
uv run pytest tests/acqstore_server/v2/test_schemas.py
uv run pytest tests/acqstore_server/v2/test_documentation_contract.py
uv run pytest tests/acqstore_server
uv run ruff check src/acqstore_server tests/acqstore_server
```

## Files changed

- `tests/acqstore_server/v2/test_schemas.py`
- `tests/acqstore_server/v2/test_documentation_contract.py`
- `docs-dev/acqstore_server/v2/javascript-client.md`
- `docs-dev/acqstore_server/v2/api.md`
- `docs-dev/acqstore_server/v2/README.md`
- `docs-dev/acqstore_server/tickets/ticket_017_javascript_client_handoff_guide.md`

## Next steps

Harden the complete v2 request/response contract with concrete examples, align OpenAPI descriptions with the written guide, and ensure the maintained demo exercises the documented lifecycle.
