# AcqStore Server API v2

API v2 is the active development API. It is a general AcqStore HTTP interface and does not assign biological roles to source channels.

## Implemented

- strict camelCase Pydantic request and response schemas;
- generic ordered `channelIndices` selection;
- AcqImage-backed loading with transport-neutral internal models;
- calibrated two-dimensional source and reference planes;
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

## Compatibility boundary

API v1 remains frozen for the neuronal linescan analyzer v1.18_b client. V2 code does not import the v1 `routes`, `schemas`, `open_service`, or `session_store` modules.

## Design rules

- Internal models use Python `snake_case` names.
- Internal models do not contain HTTP URLs.
- JSON aliases and URLs are created only at the HTTP schema/route boundary.
- Channels are identified by source index, never by calcium/vessel roles.
- The server reports array orientation and AcqStore coordinates without applying client display transposes.
- `src/acqstore/` is read-only and is inspected before using AcqStore APIs.
