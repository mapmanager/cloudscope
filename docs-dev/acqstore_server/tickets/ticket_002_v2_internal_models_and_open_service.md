# Ticket 002 — v2 internal models and open service

## Scope

Add the first transport-neutral acquisition-loading layer for API v2 without
calling or modifying the API v1 open service.

## Files added

- `src/acqstore_server/v2/models.py`
- `src/acqstore_server/v2/open_service.py`
- `tests/acqstore_server/v2/test_open_service.py`
- `tests/acqstore_server/v2/test_reference.py`

## Design decisions

- Internal models use snake_case and contain no JSON aliases or HTTP URLs.
- Channel selection is generic and index-based.
- Omitted channel selection loads all source channels.
- Requested channel order is preserved.
- Source NumPy arrays and source dtype remain intact in the service layer.
- The service reports the served plane as array dimensions `Y` and `X` with
  physical step and unit metadata from AcqStore.
- Reference arrays and scan coordinates remain in AcqStore convention. The
  server does not encode the existing HTML client's Plotly transpose behavior.
- Binary float32 conversion and URL construction remain future route/session
  transport responsibilities.

## Compatibility

No API v1 production file was edited. The v2 service imports AcqStore directly
and does not import `acqstore_server.open_service`, `schemas`, or
`session_store`.

## Validation

- Python syntax compilation is required for this slice.
- Targeted pytest commands are documented in the ZIP summary.
