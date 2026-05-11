#!/usr/bin/env bash
# Build CloudScope.app locally with nicegui-pack.
#
# Run from repo root:
#   ./packaging/macos/build_app.sh
#
# Smoke test after build:
#   open packaging/macos/dist/CloudScope.app
#
# Notes:
# - This script does NOT codesign or notarize.
# - Build outputs stay under packaging/macos/dist and packaging/macos/build.
# - All app-specific knobs live in packaging/macos/_config.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_config.sh"

cd "$SCRIPT_DIR"

echo "[build] Repo root : $REPO_ROOT"
echo "[build] App name  : $APP_NAME"
echo "[build] Bundle ID : $BUNDLE_ID"
echo "[build] Main py   : $MAIN_PY"
echo "[build] Dist dir  : $DIST_DIR"
echo "[build] Build dir : $BUILD_DIR"

if [[ ! -f "$MAIN_PY" ]]; then
  echo "ERROR: MAIN_PY not found: $MAIN_PY" >&2
  exit 2
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv is not installed or not on PATH." >&2
  exit 2
fi

if [[ ! -d "$BUILD_VENV_DIR" ]]; then
  echo "[build] Creating build venv: $BUILD_VENV_DIR"
  uv venv "$BUILD_VENV_DIR"
fi

# shellcheck source=/dev/null
source "$BUILD_VENV_DIR/bin/activate"

echo "[build] Python: $(python -V)"

echo "[build] Installing build toolchain and local project..."
uv pip install --upgrade pip >/dev/null
uv pip install pyinstaller
uv pip install -e "$REPO_ROOT"

if ! command -v nicegui-pack >/dev/null 2>&1; then
  echo "ERROR: nicegui-pack not found on PATH after installing local project." >&2
  echo "       nicegui-pack is provided by nicegui." >&2
  exit 2
fi

echo "[build] nicegui-pack: $(command -v nicegui-pack)"

_remove_dir_with_retries() {
  local d="$1"
  local attempts="${2:-6}"
  local delay="${3:-0.2}"

  [[ -d "$d" ]] || return 0
  for _ in $(seq 1 "$attempts"); do
    xattr -c -r "$d" 2>/dev/null || true
    chmod -N "$d" 2>/dev/null || true
    chmod -R u+rwX "$d" 2>/dev/null || true
    chflags -R nouchg,noschg "$d" 2>/dev/null || true
    rm -rf "$d" 2>/dev/null || true
    [[ -d "$d" ]] || return 0
    sleep "$delay"
  done

  echo "ERROR: failed to remove '$d'." >&2
  exit 1
}

echo "[build] Cleaning dist/build..."
_remove_dir_with_retries "$DIST_DIR"
_remove_dir_with_retries "$BUILD_DIR"
mkdir -p "$DIST_DIR" "$BUILD_DIR"

# Runtime mode inside the packaged app.
export CLOUDSCOPE_NATIVE=1
export CLOUDSCOPE_REMOTE=0
export CLOUDSCOPE_RELOAD=0
export CLOUDSCOPE_STORAGE_SECRET="${CLOUDSCOPE_STORAGE_SECRET:-cloudscope-packaged-app-secret}"

bash "$SCRIPT_DIR/build_info.sh"

ARGS=(
  --windowed
  --clean
  --name "$APP_NAME"
  --osx-bundle-identifier "$BUNDLE_ID"
)

if [[ -n "${ICON_PATH:-}" && -f "$ICON_PATH" ]]; then
  ARGS+=(--icon "$ICON_PATH")
  echo "[build] Icon: $ICON_PATH"
else
  echo "[build] Icon: none"
fi

echo "[build] Running nicegui-pack..."
(
  cd "$SCRIPT_DIR"
  nicegui-pack "${ARGS[@]}" "$MAIN_PY"
)

if [[ ! -d "$APP_PATH" ]]; then
  echo "ERROR: expected app not found: $APP_PATH" >&2
  exit 3
fi

bash "$SCRIPT_DIR/set_plist_versions.sh"

if [[ -f "$BUILD_INFO_PATH" ]]; then
  rm -f "$BUILD_INFO_PATH"
  echo "[build] Removed transient build info: $BUILD_INFO_PATH"
fi

echo ""
echo "[build] Done: $APP_PATH"
echo "[build] Smoke test:"
echo "  open '$APP_PATH'"
