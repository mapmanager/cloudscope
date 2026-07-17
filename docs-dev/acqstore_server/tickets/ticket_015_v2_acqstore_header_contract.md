# Ticket 015 — v2 AcqStore header contract

## Goal

Expose AcqStore's normalized image header to thin v2 clients and repair the timeout
regression test introduced when the v2 opener became injectable.

## Scope

- `src/acqstore_server/v2/` internal model, adapter, schema, and route mapping.
- Maintained v2 demo header display.
- v2 tests and documentation.
- No v1 route, v1 demo, external client, packaging, or `src/acqstore/` changes.

## Implementation

- Read the public `ImageHeader.as_json_dict()` result from `AcqImage.images.header`.
- Add transport-neutral `AcquisitionHeader` data to `OpenedAcquisition`.
- Add a strict camelCase `header` object to successful v2 open responses.
- Display the header in `/demo/v2/`.
- Update the timeout test to pass `slow_open` through `create_app(v2_open_fn=...)`.

## Validation

Run:

```bash
uv run pytest tests/acqstore_server
uv run ruff check src/acqstore_server tests/acqstore_server
```

## Files changed

- `src/acqstore_server/v2/models.py`
- `src/acqstore_server/v2/open_service.py`
- `src/acqstore_server/v2/schemas.py`
- `src/acqstore_server/v2/routes.py`
- `src/acqstore_server/static/demo/v2/index.html`
- `tests/acqstore_server/v2/test_open_service.py`
- `tests/acqstore_server/v2/test_api.py`
- `docs-dev/acqstore_server/v2/README.md`
- `docs-dev/acqstore_server/v2/api.md`
- `docs-dev/acqstore_server/v2/demo.md`
- this ticket file

## Next steps

Continue improving the generic v2 client contract and maintained demo without changing
the frozen v1 API.
