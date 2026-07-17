# AcqStore Server API v2

AcqStore Server v2 exposes the Python **AcqStore** API over local HTTP. It uses AcqStore, including `AcqImage`, to open scientific image acquisitions and make image planes, reference images, calibrated coordinates, and metadata available to thin clients.

## Intended clients

A v2 client is a thin HTTP client that connects to a running AcqStore Server. The maintained example is the generic JavaScript demo at:

```text
/demo/v2/
```

A client developer can focus on visualization and interaction while AcqStore handles acquisition loading behind the server. A running server process is always required.

- JavaScript developers and end users normally run the packaged macOS app supplied by the AcqStore Server developers. It is currently available on request from Robert Cudmore at `robert.cudmore@gmail.com`.
- Python developers may run the server from source.

## Run from source

```bash
uv run python -m acqstore_server
```

Then open:

```text
http://127.0.0.1:8767/demo/v2/
```

Optional native NiceGUI status window:

```bash
ACQSTORE_SERVER_NATIVE=1 uv run python -m acqstore_server
```

## Implemented

- strict camelCase Pydantic request and response schemas;
- generic ordered `channelIndices` selection;
- AcqImage-backed loading with transport-neutral internal models;
- calibrated two-dimensional source and reference planes;
- normalized AcqStore acquisition header metadata in every successful open response;
- raw little-endian float32 binary transport;
- independent TTL session storage;
- session metadata and explicit session deletion;
- runtime capabilities derived from AcqStore's public extension API;
- maintained JavaScript demo at `/demo/v2/`;
- isolated v2 tests and OpenAPI coverage.

## Documents

- [API reference](api.md)
- [Architecture](architecture.md)
- [Demo client](demo.md)
- [JavaScript client](javascript-client.md)
- [Python client](python-client.md)
- [Format validation](format-validation.md)
- [Testing boundary](testing.md)

## Compatibility boundary

API v1 remains frozen for existing clients. V2 code does not import the v1 `routes`, `schemas`, `open_service`, or `session_store` modules.

## Design rules

- AcqStore owns acquisition decoding and interpretation.
- AcqStore Server owns the HTTP contract, sessions, and binary transport.
- Internal models use Python `snake_case` names.
- Internal models do not contain HTTP URLs.
- JSON aliases and URLs are created only at the HTTP schema/route boundary.
- Channels are identified by source index, never by application-specific roles.
- The server reports array orientation and AcqStore coordinates without applying client display transposes.
- `src/acqstore/` is read-only and is inspected before using AcqStore APIs.

## Discovering the API

Start with:

```text
GET /api/v2
```

This returns stable links to the health check, runtime capabilities, open endpoints, OpenAPI document, interactive documentation, and maintained browser demo.

For machine-generated clients, the recommended inputs are:

1. `GET /api/v2`
2. `GET /openapi.json`
3. this documentation directory
4. the maintained JavaScript client at `/demo/v2/`
