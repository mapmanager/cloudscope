# AcqStore Server

AcqStore Server is a lightweight local HTTP server that exposes AcqStore through a stable HTTP API. It is intended for browser applications, JavaScript clients, and other tools that need to load scientific acquisitions without embedding microscope file readers.

## Start here

If you are building a new browser or JavaScript client, read **client-roadmap.md**.

That document is the complete onboarding guide and should be sufficient to build a working client.

Everything under `reference/` is lookup documentation that you can consult later if needed.

Existing API v1 integrations should continue using the documentation under `v1/`.

## Interactive API documentation

While the server is running:

- OpenAPI UI: `http://127.0.0.1:8767/docs`
- OpenAPI JSON: `http://127.0.0.1:8767/openapi.json`

## Repository layout

- `client-roadmap.md` — onboarding guide
- `reference/` — detailed API and implementation reference
- `tickets/` — development history
- `v1/` — archived v1 documentation
