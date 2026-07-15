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

A dedicated GitHub Actions workflow can mirror `.github/workflows/build-macos.yml`
with paths pointed at `packaging/acqstore_server/` (same secrets, distinct
`NOTARY_PROFILE` name optional). Not added in this pass — run the local chain first.

## Files not tracked

```text
_secrets.sh
.venv-build/
build/
dist/
*.spec
```
