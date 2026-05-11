#!/usr/bin/env bash
# Shared configuration for the CloudScope macOS packaging pipeline.
#
# This file is the single source of truth for app-specific build variables.
# To adapt this packaging folder for another NiceGUI app, edit this file first.

set -euo pipefail

# Directory of the script that sourced this file.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Repo root: packaging/macos -> repo root.
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ---- Required app-specific knobs ----
export APP_NAME="${APP_NAME:-CloudScope}"
export PYPI_PACKAGE="${PYPI_PACKAGE:-cloudscope}"
export BUNDLE_ID="${BUNDLE_ID:-com.mapmanager.cloudscope}"
export MAIN_PY="${MAIN_PY:-$REPO_ROOT/src/cloudscope/app.py}"

# Optional icon. By default this packaging folder includes assets/CloudScope.icns.
DEFAULT_ICON="$SCRIPT_DIR/assets/CloudScope.icns"
if [[ -f "$DEFAULT_ICON" ]]; then
  export ICON_PATH="${ICON_PATH:-$DEFAULT_ICON}"
else
  export ICON_PATH="${ICON_PATH:-}"
fi

# Output locations are intentionally scoped to packaging/macos/.
export DIST_DIR="${DIST_DIR:-$SCRIPT_DIR/dist}"
export BUILD_DIR="${BUILD_DIR:-$SCRIPT_DIR/build}"
export BUILD_VENV_DIR="${BUILD_VENV_DIR:-$SCRIPT_DIR/.venv-build}"

# Build-info module. Scripts write/remove this file if src/cloudscope exists.
export BUILD_INFO_PATH="${BUILD_INFO_PATH:-$REPO_ROOT/src/cloudscope/_build_info.py}"

# Derived paths.
export APP_PATH="${APP_PATH:-$DIST_DIR/${APP_NAME}.app}"
export APP_PLIST="${APP_PLIST:-$APP_PATH/Contents/Info.plist}"
export APP_MAIN_BIN="${APP_MAIN_BIN:-$APP_PATH/Contents/MacOS/${APP_NAME}}"
export PRE_NOTARIZE_ZIP="${PRE_NOTARIZE_ZIP:-$DIST_DIR/${APP_NAME}-pre-notarize.zip}"
export NOTARY_SUBMISSION_ID_FILE="${NOTARY_SUBMISSION_ID_FILE:-$DIST_DIR/notary_submission_id.txt}"

# NiceGUI runtime defaults used inside packaged .app.
export CLOUDSCOPE_NATIVE="${CLOUDSCOPE_NATIVE:-1}"
export CLOUDSCOPE_REMOTE="${CLOUDSCOPE_REMOTE:-0}"
export CLOUDSCOPE_RELOAD="${CLOUDSCOPE_RELOAD:-0}"
export CLOUDSCOPE_STORAGE_SECRET="${CLOUDSCOPE_STORAGE_SECRET:-cloudscope-packaged-app-secret}"

# Release artifact naming.
export RELEASE_PLATFORM="${RELEASE_PLATFORM:-macos}"
