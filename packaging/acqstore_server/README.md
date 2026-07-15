# AcqStore Server macOS packaging

This folder builds, signs, and notarizes `AcqStore Server.app` (NiceGUI native
status UI + localhost API). It follows the same modular script pattern as
[`packaging/macos/`](../macos/) (CloudScope).

## Source of truth

App-specific knobs live in:

```bash
packaging/acqstore_server/_config.sh
```

**Generalization hint:** to package another NiceGUI app, copy this folder (or
`packaging/macos/`), edit `_config.sh` (`APP_NAME`, `BUNDLE_ID`, `MAIN_PY`,
`RELEASE_SLUG`), keep the sign/notarize/staple scripts as-is.

| Variable | Role |
|----------|------|
| `APP_NAME` | Display / `.app` name (`AcqStore Server`) |
| `RELEASE_SLUG` | Zip basename without spaces (`AcqStore-Server`) |
| `BUNDLE_ID` | `com.mapmanager.acqstore-server` |
| `MAIN_PY` | `src/acqstore_server/desktop.py` |

## Local build only (unsigned)

```bash
./packaging/acqstore_server/build_app.sh
open "packaging/acqstore_server/dist/AcqStore Server.app"
```

Does **not** codesign or notarize.

## Signing / notarization setup

```bash
cp packaging/acqstore_server/_secrets.example.sh packaging/acqstore_server/_secrets.sh
chmod 600 packaging/acqstore_server/_secrets.sh
# edit SIGN_ID and NOTARY_PROFILE
```

You can reuse the same Developer ID identity and `notarytool` keychain profile
as CloudScope.

## Manual release chain

```bash
./packaging/acqstore_server/build_app.sh
# smoke-test unsigned app, then:
./packaging/acqstore_server/codesign_and_zip.sh
./packaging/acqstore_server/notary_submit.sh
./packaging/acqstore_server/notary_poll_until_done.sh
./packaging/acqstore_server/staple_and_verify.sh
./packaging/acqstore_server/make_release_zip.sh
```

Or one command after a successful build:

```bash
./packaging/acqstore_server/sign_notarize_release.sh
```

Artifacts:

```text
packaging/acqstore_server/dist/
  AcqStore Server.app
  AcqStore-Server-pre-notarize.zip
  AcqStore-Server-v{version}-macos.zip
  AcqStore-Server-v{version}-macos.zip.sha256
  AcqStore-Server-v{version}-macos-manifest.json
```

Tooling: `codesign`, `xcrun notarytool`, `xcrun stapler`, `spctl`, `ditto`
(same as CloudScope; no `altool`).

## CI

GitHub Actions: [`.github/workflows/build-acqstore-server-macos.yml`](../../.github/workflows/build-acqstore-server-macos.yml)

- Triggers: `workflow_dispatch` and tags `v*.*.*` (same pattern as CloudScope)
- Scripts: `./packaging/acqstore_server/*.sh` only (never `packaging/macos/`)
- Reuses the same Developer ID / Apple secrets as CloudScope
- Writes `_secrets.sh` in CI with a distinct keychain profile name:
  `acqstore-server-ci-notary-profile`
- Uploads `AcqStore-Server-*-macos.{zip,zip.sha256,manifest.json}`

Icon: `packaging/assets/AcqStoreServer.icns` (teal **AS** monogram).

## Files not tracked

```text
_secrets.sh
.venv-build/
build/
dist/
*.spec
```
