# 041 — AcqStore Server native status UI + packaging + demo transpose

**Status:** Implementation report  
**Branch:** `feature/acqstore_server`

---

## Files changed

### Created

- `src/acqstore_server/routes.py` — shared API route registration
- `src/acqstore_server/status_ui.py` — minimal NiceGUI status page
- `src/acqstore_server/desktop.py` — pack entry (`ACQSTORE_SERVER_NATIVE=1`)
- `docs-dev/cursor_tickets/041_acqstore_server_native_pack_report.md`

### Modified

- `src/acqstore_server/static/demo/index.html` — primary calcium plane drawn with **dim0 → x**, **dim1 → y** (transpose)
- `src/acqstore_server/app.py` — API-only vs native entry (`ACQSTORE_SERVER_NATIVE`)
- `src/acqstore_server/__main__.py` — docs for both modes
- `src/acqstore_server/logging_setup.py` — soft-fail if log file not writable
- `packaging/acqstore_server/_config.sh` / `build_app.sh` — real nicegui-pack build (desktop.py)
- `docs-dev/acqstore_server/README.md`, `roadmap.md`

### Not changed

- `src/acqstore/`
- `pyproject.toml`
- Colleague calcium HTML

---

## Summary

1. **Demo:** Primary (calcium) display always **transposes** so axis-0 maps to canvas X and axis-1 to canvas Y. Reference view unchanged (spatial).
2. **Native status UI:** `ACQSTORE_SERVER_NATIVE=1` runs NiceGUI native window (URL, Open demo, health, reveal log, Quit) with the same `/api/v1/*` and `/demo/` on one port.
3. **Packaging:** `./packaging/acqstore_server/build_app.sh` packs `desktop.py` into `AcqStore Server.app`.

---

## Tests

```bash
uv run pytest tests/acqstore_server -q
```

```text
21 passed, 1 warning in 1.02s
```

---

## Follow-ups

- Run `build_app.sh` locally and smoke-open the `.app` (not run in this agent session by default — long).
- Windows pack later.
- Dock “View Log” still deferred; Reveal log button covers the need.
