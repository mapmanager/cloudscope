# 039 — AcqStore Server pick-and-open + docs layout

**Status:** Implementation report  
**Branch:** `feature/acqstore_server`  
**Design:** `036_acqstore_server_design.md`

---

## Files changed

### Created

- `src/acqstore_server/dialogs.py`
- `tests/acqstore_server/test_dialogs.py`
- `docs-dev/acqstore_server/README.md`
- `docs-dev/acqstore_server/html_integration_v0.md`
- `docs-dev/acqstore_server/entry_point_and_packaging.md`
- `docs-dev/cursor_tickets/039_acqstore_server_pick_and_open_report.md`

### Modified

- `src/acqstore_server/__main__.py` — `multiprocessing.freeze_support()` + packaging notes
- `src/acqstore_server/app.py` — real `POST /api/v1/pick-and-open`; injectable `pick_file_fn`
- `src/acqstore_server/open_service.py` — `parse_channel_overrides`, `parse_pick_extensions`
- `tests/acqstore_server/test_api_v1.py` — cancel + success pick tests

### Not changed

- `src/acqstore/`
- `pyproject.toml`

---

## Summary of implementation

1. **Entry point review:** AcqStore Server is FastAPI/uvicorn, not NiceGUI. CloudScope’s `__mp_main__` configure-only hook is NiceGUI/pywebview-specific. Added `freeze_support()` under `__main__` for future freeze; documented in `docs-dev/acqstore_server/entry_point_and_packaging.md`.
2. **`pick-and-open`:** macOS uses `osascript` `choose file`; other platforms use tkinter. Injected picker for tests. Cancel → HTTP 200 + `{ok:false,error:cancelled}`.
3. **Docs layout:** `docs-dev/acqstore_server/` holds living roadmap / Claude HTML handout; cursor tickets remain for numbered implementation reports.

---

## Tests added or modified

- `tests/acqstore_server/test_dialogs.py`
- `tests/acqstore_server/test_api_v1.py` (pick cancel/success)

---

## Exact test commands run

```bash
uv run pytest tests/acqstore_server -q
```

---

## Test results

```text
16 passed, 1 warning in 1.13s
```

(Starlette/httpx TestClient deprecation warning only.)

---

## Concerns or follow-ups

- Manual smoke: run server, call pick-and-open from browser/curl, confirm macOS dialog appears on the server machine.
- Packaging freeze still stubbed.
- Expand Claude handout if wire format drifts from `html_integration_v0.md`.
