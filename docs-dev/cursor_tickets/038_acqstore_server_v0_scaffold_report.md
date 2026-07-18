# 038 — AcqStore Server v0 scaffold (health + open + binary channels)

**Status:** Implementation report  
**Branch:** `feature/acqstore_server`  
**Design:** `036_acqstore_server_design.md`

---

## Files changed

### Created

- `src/acqstore_server/__init__.py` (empty)
- `src/acqstore_server/__main__.py`
- `src/acqstore_server/app.py`
- `src/acqstore_server/open_service.py`
- `src/acqstore_server/session_store.py`
- `src/acqstore_server/schemas.py`
- `tests/acqstore_server/__init__.py` (empty)
- `tests/acqstore_server/test_open_service.py`
- `tests/acqstore_server/test_api_v1.py`
- `packaging/acqstore_server/_config.sh`
- `packaging/acqstore_server/build_app.sh` (stub; exits 2)
- `docs-dev/cursor_tickets/038_acqstore_server_v0_scaffold_report.md`

### Not changed (intentional)

- `src/acqstore/` — used public `AcqImage` / `AcqPixels.get_plane` only
- `pyproject.toml` — not edited; `pythonpath = ["src"]` + `uv` src layout discovers the package
- Colleague calcium HTML — not in repo

---

## Summary of implementation

KISS first slice of **AcqStore Server**:

- Localhost FastAPI app (`127.0.0.1:8767` by default)
- `GET /api/v1/health`, `GET /` status JSON
- `POST /api/v1/open` — path → `AcqImage` → calibration + channel session
- `GET /api/v1/session/{id}/channel/{calcium|vessels}` — raw LE float32 row-major
- Dual-channel default `0`/`1`; single-channel omits `vessels`
- CORS `*` for local HTML clients
- `POST /api/v1/pick-and-open` route present but returns `501 not_implemented` (native dialog next)
- Packaging folder scaffold only; `build_app.sh` is a stub pointing at `uv run python -m acqstore_server`

Dev start:

```bash
uv run python -m acqstore_server
```

---

## Tests added or modified

- `tests/acqstore_server/test_open_service.py`
- `tests/acqstore_server/test_api_v1.py`

---

## Exact test commands run

```bash
uv run pytest tests/acqstore_server -q
```

---

## Test results

```text
12 passed, 1 warning in 1.21s
```

Warning is upstream Starlette/httpx TestClient deprecation only; unrelated to AcqStore Server logic.

---

## Concerns or follow-ups

- Implement macOS native `pick-and-open` next.
- Synthetic TIFFs often get coerced physical units (`1.0` / Pixels); HTML may still want to override calibration — contract returns whatever `AcqImage.get_image_physical_units()` provides.
- Frozen `.app` packaging not wired yet (`packaging/acqstore_server/build_app.sh` stub).
- HTML integration handout (Claude-optimized) still to freeze from design §7–§10 once pick-and-open lands.
