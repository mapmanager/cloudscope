# AcqStore Server — roadmap (living)

**Calcium HTML:** we do **not** edit, replace, or vend the colleague 5k-line file.  
**Our job:** stable localhost API + docs/demo that HTML authors (often Claude) can integrate.

## Sequence (KISS)

| # | Item | Status |
|---|------|--------|
| 1 | Health + open-by-path + channel binaries | Done (038) |
| 2 | macOS pick-and-open | Done (039) |
| 3 | Reference image + scan path on open session | Done (040) |
| 4 | Tiny demo HTML (`/demo/`) with kymograph + ref overlay | Done (040) |
| 5 | Logging (console + `platformdirs` file) | Done (040) |
| 6 | Packaging `.app` + minimal NiceGUI status window | Done (041) — build with `./packaging/acqstore_server/build_app.sh` |
| 7 | Windows pack / Dock “View Log” menu | Later / optional |

### Run modes

| Mode | Command |
|------|---------|
| API only (default CLI) | `uv run python -m acqstore_server` |
| Native status window | `ACQSTORE_SERVER_NATIVE=1 uv run python -m acqstore_server` or `uv run python -m acqstore_server.desktop` |
| Packaged macOS | `./packaging/acqstore_server/build_app.sh` → `AcqStore Server.app` |

Packaged Quit stops the server. CLI escape hatch: see README `kill $(lsof …8767…)`.

## Confirmed product boundaries

- AcqStore Server is a **file open API** (and optional tiny status UI later).
- External calcium analyzer HTML stays with its authors.
- Demo at `/demo/` is **ours**, not their app.
- `/api/v1/` versioning: add fields (e.g. `reference`) without renaming existing keys.

## API sticky?

Nothing has shipped to external users yet. “Sticky” means: avoid renaming fields after someone starts integrating. Adding `reference` under `/api/v1/` is fine.

## Dock right-click “View Log”?

Not easy with nicegui-pack/PyInstaller alone (needs macOS native Cocoa / privileged helper). Prefer: show `logFile` in `/` JSON, health, and a future status window; user opens that path in Finder. Revisit Dock menu only if needed.

## Dev run

```bash
uv run python -m acqstore_server
# http://127.0.0.1:8767/demo/
# http://127.0.0.1:8767/api/v1/health
# log: ~/Library/Logs/AcqStore Server/acqstore_server.log
```
