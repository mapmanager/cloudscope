# CloudScope Packaging and Release

## Purpose

This document describes operational packaging and release infrastructure. Runtime architecture is documented separately in `cloudscope_architecture.md`.

Packaging goals:

```text
- local reproducible macOS .app builds
- signed/notarized macOS release zip
- git tag tied to shipped binary
- generated build metadata available at runtime
- Docker/web deployment support
- CI test/coverage workflow
```

## macOS packaging folder

Packaging scripts live under:

```text
packaging/macos/
```

Important files:

```text
_config.sh
_secrets.example.sh
_secrets.sh           # local only, not committed
build_info.sh
build_app.sh
codesign_and_zip.sh
notary_submit.sh
notary_poll_until_done.sh
staple_and_verify.sh
make_release_zip.sh
release_pipeline.sh
README.md
assets/CloudScope.icns
```

`_config.sh` is the source of truth for app-specific packaging variables:

```text
APP_NAME
BUNDLE_ID
MAIN_PY
DIST_DIR
BUILD_DIR
APP_PATH
ICON_PATH
```

The packaging folder should be reusable by editing `_config.sh` for another app.

## Secrets

Only commit:

```text
_secrets.example.sh
```

Do not commit:

```text
_secrets.sh
```

Local secrets include:

```text
SIGN_ID
NOTARY_PROFILE
```

Find signing identity:

```bash
security find-identity -v -p codesigning
```

Create notary profile:

```bash
xcrun notarytool store-credentials my-notarytool-profile \
  --apple-id "you@example.com" \
  --team-id "TEAMID" \
  --password "app-specific-password"
```

## Local app build

Build a local macOS app:

```bash
./packaging/macos/build_app.sh
```

Run it:

```bash
open packaging/macos/dist/CloudScope.app
```

This is the first smoke-test step. Do not notarize until the local app runs.

## Generated build info

Packaging generates:

```text
src/cloudscope/_build_info.py
```

This file is generated and ignored by git. It is bundled into the app. Runtime code reads it through:

```text
src/cloudscope/build_info.py
```

The app displays build info through:

```text
AppInfoView
```

Build metadata should include:

```text
app name
version
git tag
git commit
git branch
git state
build timestamps
bundle version
python version
platform
```

The runtime app should not shell out to git.

## Full release pipeline

The authoritative release script is:

```bash
./packaging/macos/release_pipeline.sh
```

Target behavior:

```text
1. verify clean working tree
2. verify current branch is main
3. read version from pyproject.toml
4. create release branch release/vX.Y.Z
5. create annotated tag vX.Y.Z
6. checkout tag / detached HEAD
7. generate build info from that tag
8. build app
9. pause for manual smoke test
10. codesign and pre-notary zip
11. submit to Apple notarization
12. poll until accepted
13. staple and verify
14. make final release zip and manifest
15. optionally push branch/tag/main or upload release artifacts
```

Critical rule:

```text
The app must be built from the git tag, not from an arbitrary working tree.
```

That ensures the release zip has a reproducible source snapshot.

## Manual release flow

Build:

```bash
./packaging/macos/build_app.sh
```

Codesign:

```bash
./packaging/macos/codesign_and_zip.sh
```

Submit:

```bash
./packaging/macos/notary_submit.sh
```

Poll:

```bash
./packaging/macos/notary_poll_until_done.sh
```

Staple:

```bash
./packaging/macos/staple_and_verify.sh
```

Final zip:

```bash
./packaging/macos/make_release_zip.sh
```

Expected notarization verification:

```text
source=Notarized Developer ID
```

## Release artifacts

Final artifacts:

```text
packaging/macos/dist/CloudScope-X.Y.Z-macos.zip
packaging/macos/dist/CloudScope-X.Y.Z-macos-manifest.json
```

Manifest should include:

```text
version
git tag
git commit
git state
build timestamp
bundle version
artifact name
artifact sha256 if available
```

## Docker/web deployment

Docker deployment is separate from macOS app packaging.

Runtime modes:

```text
local native:
  native=True
  NiceGUI chooses local host/port

local web:
  native=False
  local browser access

remote/docker:
  native=False
  host=0.0.0.0
  port=${PORT:-8080}
```

Remote/web deployments cannot access the user's local filesystem. They can access server/container paths only.

## app.py runtime config

`src/cloudscope/app.py` should use a single run-config source of truth.

Expected env vars:

```text
CLOUDSCOPE_NATIVE
CLOUDSCOPE_REMOTE
CLOUDSCOPE_RELOAD
CLOUDSCOPE_HOST
CLOUDSCOPE_PORT
PORT
CLOUDSCOPE_STORAGE_SECRET
```

Local default should allow NiceGUI to choose host/port. Docker/remote should explicitly use `0.0.0.0` and `PORT`.

Native/window setup should run only when `native=True`.

## GitHub Actions

CI should run tests and coverage.

Current desired behavior:

```text
uv sync --frozen --group dev
uv run pytest with coverage
upload coverage to Codecov if token exists
```

Ruff is intentionally not enforced in CI until the existing lint errors are fixed.

Local lint command:

```bash
uv run ruff check .
```

Local coverage command:

```bash
uv run pytest \
  --cov=src/cloudscope \
  --cov=src/acqstore \
  --cov=src/nicewidgets \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-report=xml
```

Open coverage report:

```bash
open htmlcov/index.html
```

## Git ignore rules

Do not commit:

```text
packaging/macos/_secrets.sh
packaging/macos/build/
packaging/macos/dist/
packaging/macos/.venv-build/
src/cloudscope/_build_info.py
```

Commit:

```text
packaging/macos/*.sh
packaging/macos/_secrets.example.sh
packaging/macos/README.md
packaging/macos/assets/CloudScope.icns
```

## Stress points and improvement areas

### Release pipeline must be source-of-truth strict

Manual successful builds are useful, but releases should come from tags. Avoid shipping a zip that cannot be tied to a git commit.

### Notarization failures need logs

If notarization fails, scripts should fetch and print Apple notary logs to speed debugging.

### build_info.py cleanup must be careful

`src/cloudscope/_build_info.py` should exist during packaging but not be committed. If scripts remove it after packaging, ensure it was bundled into the app first.

### Codecov depends on repo secrets

Do not commit Codecov tokens. Use GitHub repo/org secret `CODECOV_TOKEN`.

### Docker and native mode are different products

Docker/remote web mode cannot rely on native file dialogs or local user paths. Keep runtime config explicit.
