#!/usr/bin/env bash
set -euo pipefail

# Build a macOS .app bundle for the Option C NiceGUI/pywebview demo.
#
# Run from anywhere:
#   bash scripts/cloudscope/two_page_app/gpt_solution/make_app.sh
#
# Or from this directory:
#   ./make_app.sh
#
# The resulting .app is intended for double-click testing.
#
# Runtime configuration is controlled via environment variables:
#
#   CLOUDSCOPE_DEMO_MODE=desktop
#   CLOUDSCOPE_DEMO_MODE=web
#   CLOUDSCOPE_HOST=0.0.0.0
#   CLOUDSCOPE_URL_HOST=127.0.0.1
#   PORT=8080
#
# The demo defaults to desktop mode if CLOUDSCOPE_DEMO_MODE is not set.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="${SCRIPT_DIR}/multi_window_demo.py"
APP_NAME="multi-window-demo"
BUNDLE_ID="net.mapmanager.multi-window-demo"

cd "${SCRIPT_DIR}"

if ! uv run python -c "import PyInstaller" >/dev/null 2>&1; then
  echo "PyInstaller is not installed in this uv environment."
  echo
  echo "Install it with one of:"
  echo "  uv add --dev pyinstaller"
  echo "  uv add pyinstaller"
  echo
  exit 1
fi

rm -rf build dist

uv run nicegui-pack \
  --onedir \
  --windowed \
  --name "${APP_NAME}" \
  --osx-bundle-identifier "${BUNDLE_ID}" \
  --clean \
  --noconfirm \
  "${APP}"

APP_BUNDLE="${SCRIPT_DIR}/dist/${APP_NAME}.app"
CLI_BINARY="${SCRIPT_DIR}/dist/${APP_NAME}/${APP_NAME}"

if [[ ! -d "${APP_BUNDLE}" ]]; then
  echo
  echo "Build did not produce expected macOS app bundle:"
  echo "  ${APP_BUNDLE}"
  echo
  echo "Directory contents:"
  find "${SCRIPT_DIR}/dist" -maxdepth 2 -print 2>/dev/null || true
  echo
  exit 1
fi

echo
echo "Built macOS app bundle:"
echo "  ${APP_BUNDLE}"
echo
echo "Double-click test:"
echo "  open '${APP_BUNDLE}'"
echo

if [[ -x "${CLI_BINARY}" ]]; then
  echo "CLI binary also exists:"
  echo "  ${CLI_BINARY}"
  echo
  echo "Run desktop mode from terminal:"
  echo "  CLOUDSCOPE_DEMO_MODE=desktop ${CLI_BINARY}"
  echo
  echo "Run web mode from terminal:"
  echo "  CLOUDSCOPE_DEMO_MODE=web PORT=8080 ${CLI_BINARY}"
  echo
fi
