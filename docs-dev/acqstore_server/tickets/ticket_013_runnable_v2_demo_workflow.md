# Ticket 013 — Runnable API v2 demo workflow

## Goal

Make the existing production v2 workflow immediately runnable and discoverable without adding endpoints or architecture.

## Changes

- Startup output now points to `/demo/v2/`, `/docs`, and the v2 health endpoint.
- The NiceGUI status window opens the maintained v2 demo and checks v2 health.
- The main server README and v2 docs now begin with the exact run command and browser URL.
- Added a small entry-point test proving `python -m acqstore_server` starts uvicorn and advertises the maintained demo.

## User workflow

```bash
uv run python -m acqstore_server
```

Open `http://127.0.0.1:8767/demo/v2/`, click **Pick and open**, select an acquisition, and view the served planes.

## Non-goals

- No new API endpoints.
- No new server abstractions.
- No format-decoding tests.
- No changes to `src/acqstore/`.
