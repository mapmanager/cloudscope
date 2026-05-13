#!/usr/bin/env bash
# Set macOS Info.plist version fields after nicegui-pack creates the .app.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_config.sh"

if [[ ! -f "$APP_PLIST" ]]; then
  echo "ERROR: Info.plist not found: $APP_PLIST" >&2
  exit 2
fi

APP_VERSION="$(grep -E '^version[[:space:]]*=' "$REPO_ROOT/pyproject.toml" 2>/dev/null | head -1 | sed -E 's/^version[[:space:]]*=[[:space:]]*["'\'' ]*([^"'\'' ]+)["'\'' ]*.*/\1/')"
APP_VERSION="${APP_VERSION:-0.0.0}"
BUNDLE_VERSION="$APP_VERSION"

if [[ -f "$BUILD_INFO_PATH" ]]; then
  BUNDLE_VERSION="$(PYTHONPATH="$REPO_ROOT/src" python - <<'PY'
from cloudscope import _build_info
print(_build_info.BUILD_INFO.get('build_bundle_version') or _build_info.BUILD_INFO.get('version') or '0.0.0')
PY
)"
fi

/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $APP_VERSION" "$APP_PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string $APP_VERSION" "$APP_PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $BUNDLE_VERSION" "$APP_PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :CFBundleVersion string $BUNDLE_VERSION" "$APP_PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier $BUNDLE_ID" "$APP_PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string $BUNDLE_ID" "$APP_PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleName $APP_NAME" "$APP_PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :CFBundleName string $APP_NAME" "$APP_PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName $APP_NAME" "$APP_PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string $APP_NAME" "$APP_PLIST"

echo "[plist] Updated $APP_PLIST"
echo "[plist] Version       : $APP_VERSION"
echo "[plist] BundleVersion : $BUNDLE_VERSION"
echo "[plist] Bundle        : $BUNDLE_ID"
