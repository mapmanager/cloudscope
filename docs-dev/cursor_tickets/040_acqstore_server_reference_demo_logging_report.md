# 040 — AcqStore Server reference + demo + logging

**Status:** Implementation report  
**Branch:** `feature/acqstore_server`  
**Design:** `036_acqstore_server_design.md`  
**Docs:** `docs-dev/acqstore_server/`

---

## Files changed

### Created

- `src/acqstore_server/logging_setup.py`
- `src/acqstore_server/static/demo/index.html`
- `tests/acqstore_server/test_logging_setup.py`
- `docs-dev/acqstore_server/roadmap.md`
- `docs-dev/cursor_tickets/040_acqstore_server_reference_demo_logging_report.md`

### Modified

- `src/acqstore_server/schemas.py` — `reference` / `scanPath` types
- `src/acqstore_server/session_store.py` — `SessionBuffers.reference`
- `src/acqstore_server/open_service.py` — soft-fail reference extraction; logging
- `src/acqstore_server/app.py` — `/demo/`, reference plane GET, log paths on health/root
- `tests/acqstore_server/test_open_service.py` — reference monkeypatch test
- `tests/acqstore_server/test_api_v1.py` — demo + reference HTTP tests
- `docs-dev/acqstore_server/README.md`
- `docs-dev/acqstore_server/html_integration_v0.md` — reference contract for Claude/HTML authors

### Not changed

- `src/acqstore/`
- `pyproject.toml`
- Colleague calcium HTML (not in repo)

---

## Summary of implementation

1. **Reference on open/pick-and-open:** same success payload adds `reference: null | {…}`. Binary plane at `GET /api/v1/session/{id}/reference/plane`. Includes `lineRoi`, `scanPath`, and plane spacing units. Missing reference is soft-null (does not fail channel open).
2. **Demo:** `http://127.0.0.1:8767/demo/` — pick-and-open, show metadata JSON, calcium canvas, reference + scan/line overlay.
3. **Logging:** console + rotating file under platformdirs (`~/Library/Logs/AcqStore Server/acqstore_server.log` on macOS). Logs start/bind, pick/open path, duration, errors — not pixel dumps.
4. **Roadmap** updated: packaging / NiceGUI status window next; Dock “View Log” deferred (not easy with nicegui-pack alone).

---

## Tests added or modified

- Reference open + API plane fetch
- Demo static page served
- Logging path/logger smoke

---

## Exact test commands run

```bash
uv run pytest tests/acqstore_server -q
```

---

## Test results

```text
21 passed, 1 warning in 1.06s
```

---

## Concerns or follow-ups

- Manual smoke on real OIR with reference recommended (`/demo/`).
- Packaging + optional NiceGUI status shell next (show URL, demo link, log path).
- Dock context menu “View Log” possible only with native macOS helpers — skip for KISS.
