# API v2 JavaScript demo

The maintained browser demo is the reference thin client for API v2:

```text
http://127.0.0.1:8767/demo/v2/
```

Its source is:

```text
src/acqstore_server/static/demo/v2/index.html
```

It requires a running AcqStore Server, either the packaged desktop application or a server started from source.

## Lifecycle exercised by the demo

The demo intentionally exercises the complete baseline client lifecycle:

1. `GET /api/v2/health`
2. `GET /api/v2/capabilities`
3. `POST /api/v2/pick-and-open` or `POST /api/v2/open`
4. `GET /api/v2/sessions/{sessionId}`
5. fetch each source `channels[].dataUrl`
6. fetch each optional `reference.channels[].dataUrl`
7. decode raw little-endian float32 data
8. validate `byteLength` and `plane.shape`
9. transpose immediately before canvas display
10. `DELETE /api/v2/sessions/{sessionId}`

The server uses AcqStore and `AcqImage` to open the acquisition. The demo displays the returned AcqStore header, live session metadata, source channels, optional reference channels, and the full open response.

## Orientation

The API returns the original row-major two-dimensional plane. The server never transposes it.

Immediately before canvas rendering, the demo calls `transposePlane()` for both source and reference planes. This is a demo display decision and does not alter the HTTP contract.

## Compatibility

The v2 demo is independent of the frozen v1 demo at `/demo/`. It contains no application-specific channel roles and is not tied to an external calcium client.

Keep this demo synchronized with the API reference, JavaScript guide, and OpenAPI contract tests.
