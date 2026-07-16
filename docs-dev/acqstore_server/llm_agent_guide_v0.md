# AcqStore Server — LLM / agent guide (v0)

**Audience:** Another LLM or developer continuing this work.  
**Read this first**, then the linked contracts. Do not invent API fields.

---

## What this product is

Localhost **file-open HTTP API** for calcium HTML clients (especially OIR dual-channel linescans). Optional NiceGUI **native status window**. Uses `acqstore` (`AcqImage`) for decode. **Not** CloudScope; **not** a full analysis app.

| Piece | Path | Role |
|-------|------|------|
| Server package | `src/acqstore_server/` | FastAPI routes, open service, session store, native UI |
| Tiny demo | `src/acqstore_server/static/demo/` | Same-origin contract smoke UI (`/demo/`) |
| Calcium HTML fork | `clients/neuronal_calcium_linescan/` | ~5k-line analyzer with **additive** AcqStore load + reference card |
| Tests | `tests/acqstore_server/` | `uv run pytest tests/acqstore_server/` |
| Pack | `packaging/acqstore_server/` | macOS `.app` |
| Design | `docs-dev/cursor_tickets/036_acqstore_server_design.md` | Original design (may lag; prefer this guide + OpenAPI) |

---

## Package boundaries (STRICT)

| May import | Must not import |
|------------|-----------------|
| `acqstore` | `cloudscope` |
| NiceGUI / FastAPI / stdlib | `nicewidgets` (copy small helpers locally if needed, e.g. `gui_defaults.py`) |

Do **not** invent backward-compatible aliases or restore deleted routes. Prefer fail-fast.

---

## Run (dev)

```bash
# API only (default) — best for HTML clients / debugging transfer
uv run python -m acqstore_server

# Native status window (same port + API + live log)
uv run python -m acqstore_server.desktop
```

- Bind: `127.0.0.1:8767` (`ACQSTORE_SERVER_HOST` / `ACQSTORE_SERVER_PORT`)
- Open timeout: `ACQSTORE_SERVER_OPEN_TIMEOUT_S` (default **120**)
- Log file: `~/Library/Logs/AcqStore Server/acqstore_server.log` (macOS)
- Port busy: `kill $(lsof -nP -iTCP:8767 -sTCP:LISTEN -t)`

**Native gzip:** `ui.run(..., gzip_middleware_factory=None)` is required. Default NiceGUI GZip + real float32 planes ≈ **15–20 s/GET**. See ticket `048`.

---

## API surface (do not invent)

Primary handouts:

- [`html_integration_v0.md`](html_integration_v0.md) — full open workflow for HTML
- [`reference_api_v0.md`](reference_api_v0.md) — reference planes + overlay
- Live OpenAPI: `http://127.0.0.1:8767/openapi.json` / `/docs`

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/health` | Liveness |
| POST | `/api/v1/pick-and-open` | Native OS dialog; primary HTML button |
| POST | `/api/v1/open` | Body `{ "path": "/abs/..." }` |
| GET | `/api/v1/session/{id}/channel/{calcium\|vessels}` | Raw LE float32 |
| GET | `/api/v1/session/{id}/reference/channel/{index}` | Raw LE float32; only if `reference != null` |

Deleted (do not restore): `GET …/reference/plane`, top-level `reference.url`.

**Planes:** row-major `[height][width]`, LE float32, `height*width*4` bytes.  
**Server never transposes.** Clients may transpose for display (demo + HTML fork: dim0→canvas X, dim1→canvas Y).

**Sessions:** in-memory, TTL ~600 s — fetch binaries soon after open.

---

## In-repo HTML fork (status: load + reference done)

`clients/neuronal_calcium_linescan/neuronal_calcium_linescan_analyzer_v1_18.html`

| Feature | Status |
|---------|--------|
| TIFF file inputs | Unchanged upstream |
| Load from AcqStore Server | Done (049) |
| Reference overview card | Done (050) — after Image Display, before Trace |
| Edit markers | `<!-- ACQSTORE: begin NNN … -->` … `end` |
| Edit rule | Do not delete upstream — comment out |

Integration contract: still `html_integration_v0.md` / `reference_api_v0.md`.

---

## Native status UI

- Live log = same `acqstore_server` logger → scroll area
- **Show health** → `logger.info` pretty JSON (no browser)
- Footer: `acqstore_server vX.Y.Z · host:port`
- Local `gui_defaults.py` (not `nicewidgets`)

---

## Ticket index (server work)

| Ticket | Topic |
|--------|-------|
| 036 | Design |
| 038 | Scaffold |
| 039 | pick-and-open |
| 040 | Reference + demo + logging |
| 041–044 | Pack / notarize / CI / icon |
| 045 | Open timeout; remove legacy reference plane URL |
| 046–047 | Demo UX / perf timing |
| 048 | Native GZip fix |
| 049 | HTML linescan loader |
| 050 | HTML reference overview + multiline open logs |
| 051 | Native live log / footer / Show health |
| 052 | Docs pass (this refresh) |

Reports: `docs-dev/cursor_tickets/NNN_*.md`

---

## v1 remaining (not blockers for “HTML works”)

| Item | Priority | Notes |
|------|----------|-------|
| Rebuild / notarize `.app` with 048–051 | High if shipping app | Dev `uv run` already has fixes |
| Native port-busy UX | Medium | Fail loud + kill recipe; optional “already healthy” |
| OIR calibration sanity | Investigate | Some OIRs log tiny `umPerPixel`; may be units metadata, not server bug |
| Windows pack | Later | Roadmap |
| Dock “View Log” | Later / skip | Open log file button is enough |
| Auto-scroll UI log | Nice | |

---

## Agent do / don’t

**Do**

- Match OpenAPI + handouts exactly
- Update `/demo/` in the same ticket when the HTTP API changes
- Mark HTML edits with `ACQSTORE` comments + cursor ticket
- Prefer `uv run pytest tests/acqstore_server/`

**Don’t**

- Import `cloudscope` or `nicewidgets` from `acqstore_server`
- Re-enable NiceGUI default GZip
- Restore deleted reference endpoints
- Drive-by edit repo root `README.md`
- Expand HTML analysis math / replace TIFF path
