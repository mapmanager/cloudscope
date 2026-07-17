# JavaScript client handoff

This page is the handoff checklist for a senior JavaScript developer or an expert LLM implementing a new AcqStore Server v2 client.

## Prerequisite

A running AcqStore Server is required.

- End users and JavaScript developers normally receive the packaged macOS application from the AcqStore Server developers.
- Python developers may run the server from source with `uv run python -m acqstore_server`.

Default server URL:

```text
http://127.0.0.1:8767
```

## Read in this order

1. [JavaScript client guide](javascript-client.md)
2. [API contract](api.md)
3. [Reference demo](demo.md)
4. runtime OpenAPI at `http://127.0.0.1:8767/openapi.json`

## Minimum client behavior

A correct baseline client must:

- verify `/api/v2/health`;
- inspect `/api/v2/capabilities` rather than hard-code formats;
- open through `/api/v2/pick-and-open` or `/api/v2/open`;
- retain `sessionId` while using binary URLs;
- validate binary byte length and sample count;
- decode `raw-f32-le` explicitly;
- use `plane.shape` and `plane.axes` for geometry;
- treat display transpose as a client decision;
- handle stable JSON errors;
- delete the session when finished.

## Acceptance check

The client is ready when it can reproduce the lifecycle shown by `/demo/v2/` without reading the Python implementation.
