# 043 — Demo multi-channel reference + macOS sign/notarize pipeline

**Status:** Implementation report  
**Branch:** `feature/acqstore_server`

---

## Summary

1. **Demo UX**
   - Linescan titles: `Calcium channel · channel N (dim0→x, dim1→y)` / `Vessels channel · channel N …`
   - Reference: API exposes **all** reference channels; demo lays them out in a horizontal flex-wrap grid; same scanPath/lineRoi overlay on each.

2. **API**
   - `reference.channels[]` with per-channel URLs
   - `GET /api/v1/session/{id}/reference/channel/{index}`
   - `GET …/reference/plane` kept as channel-0 alias
   - Session store holds `reference_channels: tuple[bytes, …]`

3. **Packaging**
   - Ported CloudScope sign → notarytool submit → poll → staple → release zip into `packaging/acqstore_server/`
   - Config-driven via `_config.sh` (`RELEASE_SLUG=AcqStore-Server` for zip names)
   - `sign_notarize_release.sh` one-shot chain
   - README documents generalization (edit `_config.sh` first)
   - CI workflow deferred; local chain first

---

## Files changed

- `src/acqstore_server/schemas.py`, `session_store.py`, `open_service.py`, `routes.py`
- `src/acqstore_server/static/demo/index.html`
- `tests/acqstore_server/test_api_v1.py`, `test_open_service.py`
- `docs-dev/acqstore_server/html_integration_v0.md`, `README.md`
- `packaging/acqstore_server/` — `_config.sh`, `_secrets.example.sh`, `.gitignore`,
  `codesign_and_zip.sh`, `notary_submit.sh`, `notary_poll_until_done.sh`,
  `staple_and_verify.sh`, `set_plist_versions.sh`, `make_release_zip.sh`,
  `sign_notarize_release.sh`, `README.md`, `build_app.sh` (plist patch)
- `docs-dev/cursor_tickets/043_acqstore_server_ref_channels_notarize_report.md`

---

## Tests

```bash
uv run pytest tests/acqstore_server -q
```

**Result:** 25 passed, 1 warning (Starlette TestClient deprecation).

---

## Follow-ups

- Add `.github/workflows/build-macos-acqstore-server.yml` mirroring CloudScope CI when ready.
- Dedicated AcqStore Server `.icns` (currently reuses CloudScope icon).
- Optional: extract shared packaging scripts to `packaging/common/` once a third app needs them.
