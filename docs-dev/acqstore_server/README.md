# AcqStore Server docs

Living documentation for the local **AcqStore Server** lab tool (HTTP open API for external calcium HTML clients).

## Clients

| Client | Role |
|--------|------|
| `/demo/` (`src/acqstore_server/static/demo/`) | Small same-origin API smoke UI; keep in sync with API changes |
| [`clients/neuronal_calcium_linescan/`](../../clients/neuronal_calcium_linescan/) | In-repo working fork of the ~5k-line neuronal calcium HTML; **additive** server load path (keep TIFF file load). Edit rules: do not delete upstream code (comment out); mark new blocks with `<!-- ACQSTORE: … -->` and a cursor ticket |

Handouts below are the public API contract for HTML authors (including that fork).

## Layout

| Path | Role |
|------|------|
| `README.md` | This index |
| `roadmap.md` | Living implementation sequence + product boundaries |
| `html_integration_v0.md` | Claude-optimized handout for HTML authors |
| `reference_api_v0.md` | Reference-image metadata + plane fetch contract |
| `entry_point_and_packaging.md` | `__main__` / freeze notes vs CloudScope NiceGUI |

Numbered implementation reports stay in `docs-dev/cursor_tickets/` (036 design, 038 scaffold, 039 pick-and-open, 040 reference+demo+logging).

## Design source of truth

[`../cursor_tickets/036_acqstore_server_design.md`](../cursor_tickets/036_acqstore_server_design.md)

Wire contract for HTML authors: [`html_integration_v0.md`](html_integration_v0.md) (keep in sync when API changes). Reference planes: [`reference_api_v0.md`](reference_api_v0.md).

**Demo policy:** when the HTTP API changes, update `/demo/` (`src/acqstore_server/static/demo/index.html`) in the same ticket so the bundled client stays a working contract check.

## Dev run (start / stop on macOS)

### Start (API only — default)

```bash
cd /path/to/cloudscope
uv run python -m acqstore_server
```

Leave that terminal open. **Ctrl+C** stops the server.

API-only mode does **not** run NiceGUI. If the terminal shows

```text
WebSocket /_nicegui_ws/... 403
GET /_nicegui_ws/... 404
```

that is almost always a **stale browser tab** left open from native mode (`ACQSTORE_SERVER_NATIVE=1` or the packaged `.app`). Close those tabs (or hard-refresh). The API server itself is fine if you still see `Uvicorn running on http://127.0.0.1:8767`.

### Start (native status window — same API + demo)

```bash
ACQSTORE_SERVER_NATIVE=1 uv run python -m acqstore_server
# or
uv run python -m acqstore_server.desktop
```

Quit the status window to stop the server. Buttons: Open demo, health, reveal log.

Native mode uses NiceGUI `ui.run(..., gzip_middleware_factory=None)`. NiceGUI’s
default GZip middleware must stay off: browsers send `Accept-Encoding: gzip`,
and compressing real ~20 MB float32 session planes at level 9 delayed response
headers by ~15–20 s per GET (API-only uvicorn was always fast because it never
installed that middleware). See ticket `048_native_gzip_session_fetch_fix`.

### Useful URLs

| URL | What |
|-----|------|
| http://127.0.0.1:8767/ | JSON status (API-only mode) or NiceGUI status (native mode) |
| http://127.0.0.1:8767/docs | **Interactive OpenAPI** (Swagger UI) — try endpoints |
| http://127.0.0.1:8767/redoc | Alternate API docs |
| http://127.0.0.1:8767/openapi.json | Machine-readable OpenAPI schema |
| http://127.0.0.1:8767/demo/ | demo UI (served by the server; needs a **current** server) |
| http://127.0.0.1:8767/api/v1/health | health |
| `~/Library/Logs/AcqStore Server/acqstore_server.log` | rotating log file |

### Demo HTML: server required?

Yes for a working demo. The page calls `POST /api/v1/pick-and-open` and binary session URLs. Opening `src/acqstore_server/static/demo/index.html` via `file://` can show the chrome, but the Load button still needs a running server (set `BASE` would be required). Prefer `http://127.0.0.1:8767/demo/`.

### Display transpose (demo only)

The **server never transposes** pixels. The demo JS draws with dim0→canvas X, dim1→canvas Y. Reference overlay swaps scanPath/lineRoi the same way for display.

### Packaged app: `/demo/` was 404

Frozen builds must include static files. `build_app.sh` now passes:

`--add-data src/acqstore_server/static:acqstore_server/static`

Rebuild the `.app` after pulling this change. `/demo/` is also served via explicit `FileResponse` (not only `StaticFiles`).

Default port: **8767** (override with `ACQSTORE_SERVER_PORT`).

### Stop when you lost the terminal / “address already in use”

If you see:

```text
[Errno 48] ... address already in use
```

or `/demo/` returns `{"detail":"Not Found"}` while health still works, an **old** server is still bound to 8767.

**Recipe (macOS):**

```bash
# 1) Who is listening?
lsof -nP -iTCP:8767 -sTCP:LISTEN

# 2) Stop those PIDs (graceful)
kill $(lsof -nP -iTCP:8767 -sTCP:LISTEN -t)

# 3) If still listed after ~1s, force quit
kill -9 $(lsof -nP -iTCP:8767 -sTCP:LISTEN -t)

# 4) Confirm free
lsof -nP -iTCP:8767 -sTCP:LISTEN || echo 'port 8767 is free'
```

Then start again.

**One-liner escape hatch:**

```bash
kill $(lsof -nP -iTCP:8767 -sTCP:LISTEN -t) 2>/dev/null; sleep 1; kill -9 $(lsof -nP -iTCP:8767 -sTCP:LISTEN -t) 2>/dev/null; echo done
```

### Packaged macOS app

```bash
./packaging/acqstore_server/build_app.sh
open "packaging/acqstore_server/dist/AcqStore Server.app"
```

Double-click opens the native status window and starts the API on `127.0.0.1:8767`. Quit the window to stop.

Sign / notarize / staple / release zip (same pattern as `packaging/macos/`):

```bash
# once: copy and edit secrets (can reuse CloudScope SIGN_ID / NOTARY_PROFILE)
cp packaging/acqstore_server/_secrets.example.sh packaging/acqstore_server/_secrets.sh
chmod 600 packaging/acqstore_server/_secrets.sh

./packaging/acqstore_server/build_app.sh
./packaging/acqstore_server/sign_notarize_release.sh
```

Details: [`packaging/acqstore_server/README.md`](../../packaging/acqstore_server/README.md).

CI workflow (same Apple secrets as CloudScope):  
[`.github/workflows/build-acqstore-server-macos.yml`](../../.github/workflows/build-acqstore-server-macos.yml)  
(`workflow_dispatch` or tag `v*.*.*`).

### Code changed but browser looks old?

Restart the server after pulling new code. A leftover process serves the **old** routes.

## Package code

- Runtime: `src/acqstore_server/`
- Static demo: `src/acqstore_server/static/demo/`
- Tests: `tests/acqstore_server/`
- Pack scaffold: `packaging/acqstore_server/`
