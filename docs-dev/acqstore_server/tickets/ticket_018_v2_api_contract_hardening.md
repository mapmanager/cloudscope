# Ticket 018 — v2 API contract hardening

## Goal

Make the existing AcqStore Server API v2 contract explicit and regression-tested so a senior JavaScript developer or expert LLM can implement a client without reading the Python source.

## Scope

This ticket does not add or remove endpoints. It hardens the documentation and machine-readable contract for the existing v2 lifecycle.

## Implementation

- Replaced `v2/api.md` with a complete endpoint and payload reference.
- Added concrete examples for discovery, capabilities, open responses, binary planes, references, sessions, cleanup, cancellation, and stable errors.
- Documented the relationship between AcqStore normalized headers and served two-dimensional planes.
- Added OpenAPI regression tests for every endpoint required by the JavaScript-client lifecycle.
- Added OpenAPI checks for camelCase JSON properties and binary response media types.
- Corrected the Ticket 017 documentation regression test so it validates the guide's composed JavaScript URLs instead of requiring duplicated literal endpoint strings.

## Validation

Run:

```bash
uv run pytest tests/acqstore_server/v2/test_documentation_contract.py
uv run pytest tests/acqstore_server/v2/test_openapi_contract.py
uv run pytest tests/acqstore_server
uv run ruff check src/acqstore_server tests/acqstore_server
```

## Files changed

```text
docs-dev/acqstore_server/v2/api.md
docs-dev/acqstore_server/tickets/ticket_018_v2_api_contract_hardening.md
tests/acqstore_server/v2/test_documentation_contract.py
tests/acqstore_server/v2/test_openapi_contract.py
```

## Next steps

Perform the milestone handoff pass: verify the maintained v2 demo exercises the documented lifecycle and remove any remaining documentation ambiguity for a JavaScript developer who does not use Python.
