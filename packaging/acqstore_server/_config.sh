#!/usr/bin/env bash
# Shared configuration for the AcqStore Server macOS packaging pipeline.
#
# This file is the single source of truth for app-specific build variables.
# Same pattern as packaging/macos/_config.sh — adapt a new app by copying
# packaging/acqstore_server/ (or packaging/macos/) and editing this file first.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ---- Required app-specific knobs ----
export APP_NAME="${APP_NAME:-AcqStore Server}"
# URL/path-safe slug for zip filenames (spaces in APP_NAME are awkward in CI globs).
export RELEASE_SLUG="${RELEASE_SLUG:-AcqStore-Server}"
export PYPI_PACKAGE="${PYPI_PACKAGE:-cloudscope}"
export BUNDLE_ID="${BUNDLE_ID:-com.mapmanager.acqstore-server}"
# Desktop entry enables native NiceGUI status window + same API/demo routes.
export MAIN_PY="${MAIN_PY:-$REPO_ROOT/src/acqstore_server/desktop.py}"

# Optional icon. Shared packaging assets live in packaging/assets/.
DEFAULT_ICON="$SCRIPT_DIR/../assets/CloudScope.icns"
if [[ -f "$DEFAULT_ICON" ]]; then
  export ICON_PATH="${ICON_PATH:-$DEFAULT_ICON}"
else
  export ICON_PATH="${ICON_PATH:-}"
fi

# Output locations are intentionally scoped to packaging/acqstore_server/.
export DIST_DIR="${DIST_DIR:-$SCRIPT_DIR/dist}"
export BUILD_DIR="${BUILD_DIR:-$SCRIPT_DIR/build}"
export BUILD_VENV_DIR="${BUILD_VENV_DIR:-$SCRIPT_DIR/.venv-build}"

# Optional build-info (not required for AcqStore Server v0).
export BUILD_INFO_PATH="${BUILD_INFO_PATH:-}"
export BUILD_INFO_JSON_PATH="${BUILD_INFO_JSON_PATH:-$DIST_DIR/build_info.json}"

# Derived paths.
export APP_PATH="${APP_PATH:-$DIST_DIR/${APP_NAME}.app}"
export APP_PLIST="${APP_PLIST:-$APP_PATH/Contents/Info.plist}"
export APP_MAIN_BIN="${APP_MAIN_BIN:-$APP_PATH/Contents/MacOS/${APP_NAME}}"
export PRE_NOTARIZE_ZIP="${PRE_NOTARIZE_ZIP:-$DIST_DIR/${RELEASE_SLUG}-pre-notarize.zip}"
export NOTARY_SUBMISSION_ID_FILE="${NOTARY_SUBMISSION_ID_FILE:-$DIST_DIR/notary_submission_id.txt}"

# Packaged runtime defaults.
export ACQSTORE_SERVER_HOST="${ACQSTORE_SERVER_HOST:-127.0.0.1}"
export ACQSTORE_SERVER_PORT="${ACQSTORE_SERVER_PORT:-8767}"
export ACQSTORE_SERVER_NATIVE="${ACQSTORE_SERVER_NATIVE:-1}"

# Release artifact naming.
export RELEASE_PLATFORM="${RELEASE_PLATFORM:-macos}"
