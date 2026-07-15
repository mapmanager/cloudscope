# 042 — Demo UX + OpenAPI docs + frozen /demo/ fix

**Status:** Implementation report  
**Branch:** `feature/acqstore_server`

---

## Answers (user Qs)

1. **Calcium height** — demo calcium canvas area uses taller target (960×400) + scrollable wrap.
2. **Where is transpose?** — **Demo JS only.** Server returns row-major `(height, width)` planes unchanged.
3. **Reference transpose** — demo now transposes reference the same way and maps scanPath/lineRoi with `(canvasX, canvasY) = (apiY, apiX)`.
4. **Two channels** — yes, previously only calcium was drawn; demo now shows a vessels panel when `channels.vessels` is present.
5. **file:// HTML?** — not practical as the primary path; API + picker need the server. Use `/demo/` from the running server.
6. **Better docs** — FastAPI OpenAPI: `/docs`, `/redoc`, `/openapi.json`. Root `hint` points at `/docs`.
7. **Packaged `/demo/` 404** — static HTML was not bundled in PyInstaller datas; NiceGUI then 404'd. Fixed with `--add-data` + `FileResponse` routes + frozen path resolution. **Rebuild the .app.**

---

## Files changed

- `src/acqstore_server/static/demo/index.html`
- `src/acqstore_server/routes.py` — `resolve_static_dir`, demo `FileResponse`
- `src/acqstore_server/app.py` — OpenAPI description; `fastapi_docs=True` in native
- `src/acqstore_server/status_ui.py` — API docs button
- `packaging/acqstore_server/build_app.sh` — `--add-data` for static/
- `tests/acqstore_server/test_api_v1.py`, `test_static_resolve.py`
- `docs-dev/acqstore_server/README.md`
- `docs-dev/cursor_tickets/042_acqstore_server_demo_docs_packfix_report.md`

---

## Tests

```bash
uv run pytest tests/acqstore_server -q
```

**Result:** 23 passed, 1 warning (Starlette TestClient deprecation).

---

## Follow-up for user

```bash
# stop old server if needed, then rebuild app
./packaging/acqstore_server/build_app.sh
open "packaging/acqstore_server/dist/AcqStore Server.app"
# Open demo → should load HTML; also try http://127.0.0.1:8767/docs
```

## Clarifications (post-ship Qs)

- **CLI + `/_nicegui_ws` 403/404:** Harmless stale NiceGUI tabs after a native session. API-only uvicorn does not serve NiceGUI. Documented in `docs-dev/acqstore_server/README.md`.
- **Colleague `file://` HTML:** Supported via CORS `*`; handout updated. They call `http://127.0.0.1:8767/...` from their page; hosting on `/demo/` is not required.
- **uvicorn factory double-init:** `main_uvicorn` now runs the module-level `app` once (no `factory=True`).
