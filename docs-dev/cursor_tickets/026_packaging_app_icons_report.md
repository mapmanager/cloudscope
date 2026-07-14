# 026 — Packaging app icons (CS master for macOS + Windows)

## Problem

macOS packaging already passed `--icon` using
`packaging/macos/assets/CloudScope.icns` (legacy **KF** monogram). Windows CI
passed no `--icon`, so Windows used the PyInstaller default. Favicon/in-app
artwork (`src/cloudscope/assets/icons/cloudscope.png`) was intentionally left
alone.

## Files changed

- `packaging/assets/CloudScope.png` — generated 1024×1024 master (**CS**, KF layout)
- `packaging/assets/CloudScope.icns` — macOS multi-resolution icon
- `packaging/assets/CloudScope.ico` — Windows multi-size icon
- `packaging/assets/build_icons.sh` — regenerate `.icns`/`.ico` from master
- `packaging/assets/README.md` — short asset index
- `packaging/macos/_config.sh` — `ICON_PATH` → `../assets/CloudScope.icns`
- `packaging/macos/assets/CloudScope.icns` — removed (legacy KF)
- `.github/workflows/build-windows.yml` — `--icon packaging/assets/CloudScope.ico`
- `docs-dev/cursor_tickets/026_packaging_app_icons_report.md` — this report

macOS CI unchanged beyond `_config.sh` / shared assets (still calls
`build_app.sh`).

## Summary of implementation

Committed master PNG plus platform icons. Builds consume native formats
(`.icns` / `.ico`). Helper script is optional for future art updates; day-to-day
packaging does not require running it.

## Tests added or modified

None.

## Exact test commands run

```bash
# _config resolves new icns
source packaging/macos/_config.sh  # via scripted check: ICON_PATH OK
./packaging/assets/build_icons.sh
file packaging/assets/CloudScope.{png,icns,ico}
```

## Test results

- Master: PNG 1024×1024 RGBA
- `.icns`: Mac OS X icon, 1024×1024
- `.ico`: MS Windows icon, 6 sizes through 256×256
- `_config.sh` points at `packaging/assets/CloudScope.icns`

Full `./packaging/macos/build_app.sh` / Finder Dock icon check: not re-run in
this ticket.

## Concerns or follow-ups

- After rebuild, macOS may cache old Dock icons; logout/reboot or clear icon
  cache if CS does not appear immediately.
- Confirm Windows artifact Dock/Explorer icon via `workflow_dispatch` or local
  Windows pack when available.
- In-app favicon remains the green-striped PNG by design.
