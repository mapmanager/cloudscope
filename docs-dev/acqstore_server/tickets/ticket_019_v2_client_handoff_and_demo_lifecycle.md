# Ticket 019 — v2 client handoff and demo lifecycle

## Goal

Complete the milestone handoff pass so a senior JavaScript developer or expert LLM can understand and exercise the full baseline v2 lifecycle without reading Python source.

## Scope

- Correct the OpenAPI camelCase regression test to match the actual schema ownership.
- Make the maintained v2 demo exercise health, capabilities, open, session inspection, binary fetch, transpose-for-display, and session deletion.
- Add a concise JavaScript-client handoff checklist.
- Keep v1 runtime and clients unchanged.

## Implementation

- `ApiIndexResponse` is tested for `apiVersion`; `OpenResponse` is tested only for fields it actually owns.
- CamelCase checks now cover header, channel, plane, axis, and binary encoding schemas.
- The demo displays server readiness and live session metadata.
- Demo regression coverage protects the complete client lifecycle.
- Documentation points new client developers to one ordered handoff path.

## Validation

Run:

```bash
uv run pytest tests/acqstore_server/v2/test_openapi_contract.py
uv run pytest tests/acqstore_server/v2/test_demo.py
uv run pytest tests/acqstore_server
uv run ruff check src/acqstore_server tests/acqstore_server
```

## Files changed

- `src/acqstore_server/static/demo/v2/index.html`
- `tests/acqstore_server/v2/test_openapi_contract.py`
- `tests/acqstore_server/v2/test_demo.py`
- `docs-dev/acqstore_server/v2/README.md`
- `docs-dev/acqstore_server/v2/demo.md`
- `docs-dev/acqstore_server/v2/client-handoff.md`
- this ticket

## Next steps

Perform one final milestone audit for contradictions, missing links, and client-visible contract gaps before declaring JavaScript-client handoff ready.
