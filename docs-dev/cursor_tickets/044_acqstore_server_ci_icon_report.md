# 044 — AcqStore Server macOS CI workflow + AS app icon

**Status:** Implementation report  
**Branch:** `feature/acqstore_server`

---

## Summary

1. **GitHub Actions** — `.github/workflows/build-acqstore-server-macos.yml`
   - Modeled on `build-macos.yml`
   - Uses **only** `./packaging/acqstore_server/*.sh` (never `packaging/macos/`)
   - Same secrets as CloudScope; CI notary profile name:
     `acqstore-server-ci-notary-profile`
   - Artifacts: `AcqStore-Server-*-macos.{zip,zip.sha256,manifest.json}`
   - Triggers: `workflow_dispatch` + tags `v*.*.*`

2. **App icon** — teal **AS** monogram (distinct from black **CS**)
   - Master: `packaging/assets/AcqStoreServer.png` (1024×1024)
   - `AcqStoreServer.icns` / `.ico` generated via `build_icons.sh`
   - `packaging/acqstore_server/_config.sh` → `AcqStoreServer.icns`

---

## Files changed

- `.github/workflows/build-acqstore-server-macos.yml` (new)
- `packaging/assets/AcqStoreServer.png`, `.icns`, `.ico` (new)
- `packaging/assets/build_icons.sh` — multi-app (`CloudScope` / `AcqStoreServer`)
- `packaging/assets/README.md`
- `packaging/acqstore_server/_config.sh`
- `packaging/acqstore_server/README.md`
- `docs-dev/cursor_tickets/044_acqstore_server_ci_icon_report.md`

---

## Tests

```bash
./packaging/assets/build_icons.sh AcqStoreServer
file packaging/assets/AcqStoreServer.{png,icns,ico}
bash -c 'source packaging/acqstore_server/_config.sh && test -f "$ICON_PATH" && echo OK'
```

**Results:**
- PNG 1024×1024 RGBA
- `.icns` Mac OS X icon
- `.ico` 6 sizes
- `_config.sh` ICON_PATH points at `AcqStoreServer.icns` → OK

Workflow not executed on runners in this ticket (requires secrets + macos-14).

---

## Follow-ups

- Rebuild `.app` locally to pick up AS Dock icon: `./packaging/acqstore_server/build_app.sh`
- Run `workflow_dispatch` on `Build AcqStore Server macOS` when ready to exercise CI.
- macOS may cache Dock icons after rebuild; logout/reboot if AS does not appear.
