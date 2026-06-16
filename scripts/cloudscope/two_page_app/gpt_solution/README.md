# NiceGUI Multi-Window / Multi-Tab Demo

This directory contains the current reference demo for CloudScope-style two-surface UI.

The demo intentionally does **not** use `ui.run(native=True)`. Instead it runs one NiceGUI server and points multiple UI surfaces at routes on that server.

## Desktop mode

Desktop mode starts a local NiceGUI server with `native=False, show=False`, then creates pywebview windows manually:

- `/` opens in the Main desktop window.
- `/pool` opens in the Pool desktop window.

Both windows share one in-memory `AppStore`.

Run locally:

```bash
CLOUDSCOPE_DEMO_MODE=desktop uv run python multi_window_demo.py
```

The mode defaults to `desktop`, so this also works:

```bash
uv run python multi_window_demo.py
```

## Web mode

Web mode runs one normal NiceGUI server. The Main tab opens `/pool` in a second browser tab.

Run locally on port 8080:

```bash
CLOUDSCOPE_DEMO_MODE=web PORT=8080 uv run python multi_window_demo.py
```

Then visit:

```text
http://localhost:8080
```

## Docker web test

Docker/Oracle mode should use web mode only. Desktop pywebview windows are not used in Docker. The compose file maps host port `8081` to container port `8080` so it can run beside the main CloudScope app.

```bash
docker compose up --build -d
```

Then visit:

```text
http://localhost:8081
```

Stop the demo:

```bash
docker compose down
```

## macOS app bundle test

Build a double-clickable `.app`:

```bash
./make_app.sh
```

Then run:

```bash
open dist/multi-window-demo.app
```

## Environment variables

- `CLOUDSCOPE_DEMO_MODE=desktop` or `web`; defaults to `desktop`.
- `CLOUDSCOPE_HOST`; defaults to `127.0.0.1` in desktop mode and `0.0.0.0` in web mode.
- `CLOUDSCOPE_URL_HOST`; defaults to `127.0.0.1` for desktop pywebview URLs.
- `PORT`; defaults to `8080` in web mode. In desktop mode, if unset, a free local port is selected.

## Current known behavior

- Closing the pool window closes only the pool window.
- Closing the main desktop window closes the pool window if open and then shuts down the app.
- In web mode, clicking Open Pool opens `/pool` in another browser tab.
- The demo uses one in-memory `AppStore`. A production CloudScope web server must scope state per user/session.
