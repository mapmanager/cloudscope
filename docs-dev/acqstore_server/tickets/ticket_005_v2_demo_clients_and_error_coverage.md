# Ticket 005 — API v2 demo, clients, and error coverage

## Scope

Add and maintain a versioned browser client for API v2 while leaving the frozen
v1 demo unchanged. Extend route coverage for timeout and invalid binary indices.

## AcqStore API inspection

This slice adds no new AcqStore calls. It relies only on the already verified v2
open-service boundary. No file under `src/acqstore/` was edited.

## Added

- `src/acqstore_server/v2/demo.py`
- `src/acqstore_server/static/demo/v2/index.html`
- `tests/acqstore_server/v2/test_demo.py`
- timeout and binary-index tests in `test_api.py`
- v2 demo, JavaScript-client, and Python-client documentation

## Edited

- `src/acqstore_server/app.py` registers `/demo/v2/` in FastAPI and NiceGUI modes.

## Contract decisions

- `/demo/` remains the frozen v1 demo.
- `/demo/v2/` is the maintained v2 demo.
- The demo dynamically renders arbitrary source and reference channels.
- Canvas orientation is explicitly a client display decision.
- The demo consumes `dataUrl`, `byteLength`, `plane.shape`, and `plane.axes`.

## Validation

Run:

```bash
uv run pytest tests/acqstore_server
uv run ruff check src/acqstore_server tests/acqstore_server
```
