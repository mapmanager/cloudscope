# CloudScope macOS packaging

This folder contains the local and release packaging scripts for building a macOS `CloudScope.app` with `nicegui-pack`.

## Source of truth

Most app-specific build variables are defined in:

```bash
packaging/macos/_config.sh
```

To adapt this folder for another app, start by editing `_config.sh`.

## Local build only

From the repo root:

```bash
./packaging/macos/build_app.sh
open packaging/macos/dist/CloudScope.app
```

This builds a local unsigned app for smoke testing. It does not codesign, notarize, staple, or create a release zip.

During the build, `build_info.sh` writes a transient generated module:

```text
src/cloudscope/_build_info.py
```

That module is bundled into the app and then removed from the working tree after packaging. It is intentionally ignored by git.

## Signing/notarization setup

Create local secrets, but do not commit them:

```bash
cp packaging/macos/_secrets.example.sh packaging/macos/_secrets.sh
chmod 600 packaging/macos/_secrets.sh
```

Edit `_secrets.sh` with your `SIGN_ID` and `NOTARY_PROFILE`.

## Manual release steps

After `build_app.sh` works and you are ready to sign/notarize:

```bash
./packaging/macos/codesign_and_zip.sh
./packaging/macos/notary_submit.sh
./packaging/macos/notary_poll_until_done.sh
./packaging/macos/staple_and_verify.sh
./packaging/macos/make_release_zip.sh
```

Artifacts are written under:

```text
packaging/macos/dist/
```

## Full release pipeline

The full pipeline creates a release branch/tag, checks out the tag, builds from that exact source, signs, notarizes, staples, zips, pushes the tag and release branch, merges back to main, and optionally uploads artifacts with `gh`:

```bash
./packaging/macos/release_pipeline.sh
```

The pipeline pauses after the app build for a manual smoke test:

```bash
open packaging/macos/dist/CloudScope.app
```

Press Enter to continue to codesign/notarize, or Ctrl-C to abort. For automation, set:

```bash
CLOUDSCOPE_RELEASE_NO_PAUSE=1 ./packaging/macos/release_pipeline.sh
```

## Files intentionally not tracked

```text
_secrets.sh
.venv-build/
build/
dist/
*.spec
src/cloudscope/_build_info.py
```
