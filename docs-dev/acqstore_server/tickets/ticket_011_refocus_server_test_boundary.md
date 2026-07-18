# Ticket 011 — Refocus the AcqStore Server test boundary

## Goal

Keep API v2 tests focused on server behavior rather than duplicating AcqStore's
microscopy-format loader tests.

## Decision

AcqStore owns correctness for decoding TIFF, OIR, CZI, ND2, and other formats.
AcqStore Server assumes the public AcqStore API returns a valid acquisition and
tests how that result is exposed over HTTP.

A small number of adapter tests may still use a simple TIFF fixture to verify
that the server's AcqStore integration has not drifted. The server suite should
not maintain optional collections of real microscope files or assert detailed
format-specific decoding behavior.

## Changes

- Added an injectable API v2 open function at the application/router boundary.
- Replaced Ticket 010's optional local-file harness with deterministic
  `OpenedAcquisition` fixtures.
- Retained the two Ticket 010 filenames so rsync-based replacement merges
  overwrite them without requiring manual deletion.
- Added tests for channel-selection forwarding, generic serialization, binary
  encoding, and format-label neutrality.

## Boundary

The injected opener is a test seam only. Production defaults continue to call
`acqstore_server.v2.open_service.open_acquisition`, which uses the verified,
read-only public AcqStore API.

## Files edited

- `src/acqstore_server/app.py`
- `src/acqstore_server/v2/routes.py`
- `tests/acqstore_server/v2/representative_files.py`
- `tests/acqstore_server/v2/test_representative_formats.py`

## Validation

Run:

```bash
uv run pytest tests/acqstore_server
uv run ruff check src/acqstore_server tests/acqstore_server
```
