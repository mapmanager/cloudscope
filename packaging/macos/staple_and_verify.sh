#!/usr/bin/env bash
# Staple the notarization ticket and verify Gatekeeper acceptance.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_config.sh"

if [[ ! -d "$APP_PATH" ]]; then
  echo "ERROR: App not found: $APP_PATH" >&2
  exit 2
fi

echo "[staple] Stapling: $APP_PATH"
xcrun stapler staple "$APP_PATH"

echo "[staple] Assessing with spctl..."
spctl --assess --type execute --verbose=4 "$APP_PATH"

echo "[staple] Done."
