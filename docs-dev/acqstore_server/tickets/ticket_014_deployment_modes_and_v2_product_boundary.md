# Ticket 014 — Deployment modes and v2 product boundary

## Goal

Make the AcqStore dependency, thin-client purpose, and two supported deployment modes explicit while keeping API v2 as the default visible workflow.

## Scope

- `src/acqstore_server/`
- `tests/acqstore_server/`
- `docs-dev/acqstore_server/`

## Changes

- Reframed AcqStore Server as an HTTP exposure layer for the AcqStore/AcqImage API.
- Distinguished source-based Python development from packaged desktop use.
- Clarified that thin clients always require a running server.
- Removed application-specific calcium-client framing from the main and v2 documentation.
- Changed terminal and native status UI links from the frozen v1 demo/health routes to v2.
- Added regression coverage for the visible v2 startup workflow.

## Non-goals

- No new endpoint.
- No changes to AcqStore.
- No changes to external clients.
- No packaging workflow changes.
