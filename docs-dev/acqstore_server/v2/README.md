# AcqStore Server API v2

API v2 is the active development API. It is a general AcqStore HTTP interface and does not assign biological roles to source channels.

## Current implementation status

Implemented foundation:

- strict Pydantic request and response schemas;
- generic `channelIndices` selection;
- channel-indexed in-memory session storage;
- independent `acqstore_server.v2` package;
- isolated tests under `tests/acqstore_server/v2`.

Not yet implemented:

- AcqImage loading service;
- v2 HTTP routes;
- application registration;
- reference-image transport;
- generated OpenAPI examples.

## Compatibility boundary

API v1 remains frozen for the neuronal linescan analyzer v1.18_b client. V2 code must not import the v1 `routes`, `schemas`, `open_service`, or `session_store` modules.

## Design rules

- Internal models use Python `snake_case` names.
- Internal models do not contain HTTP URLs.
- JSON aliases and URLs are created only at the HTTP schema/route boundary.
- Channels are identified by source index, never by calcium/vessel roles.
- The server reports array orientation and AcqStore coordinates without applying client display transposes.
