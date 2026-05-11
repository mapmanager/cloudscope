#!/usr/bin/env bash
# Create final distribution zip and manifest after notarization/stapling.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_config.sh"

if [[ ! -d "$APP_PATH" ]]; then
  echo "ERROR: App not found: $APP_PATH" >&2
  exit 2
fi

APP_VERSION="$(grep -E '^version[[:space:]]*=' "$REPO_ROOT/pyproject.toml" 2>/dev/null | head -1 | sed -E 's/^version[[:space:]]*=[[:space:]]*["'\'' ]*([^"'\'' ]+)["'\'' ]*.*/\1/')"
APP_VERSION="${APP_VERSION:-0.0.0}"
REL_BASENAME="${APP_NAME}-${APP_VERSION}-${RELEASE_PLATFORM}"
REL_ZIP="$DIST_DIR/${REL_BASENAME}.zip"
REL_MANIFEST="$DIST_DIR/${REL_BASENAME}-manifest.json"

echo "[release] App     : $APP_PATH"
echo "[release] Version : $APP_VERSION"

echo "[release] Gatekeeper assess..."
SPCTL_OUT="$(spctl --assess --type execute --verbose=4 "$APP_PATH" 2>&1 || true)"
echo "$SPCTL_OUT"
if ! echo "$SPCTL_OUT" | grep -qi accepted; then
  echo "ERROR: spctl did not accept the app. Run staple_and_verify.sh first." >&2
  exit 3
fi

CS_META="$(codesign -dv --verbose=4 "$APP_PATH" 2>&1 || true)"
TEAM_ID="$(echo "$CS_META" | sed -nE 's/^TeamIdentifier=([A-Z0-9]+).*/\1/p' | tail -n 1)"
SIGNING_AUTH="$(echo "$CS_META" | sed -nE 's/^Authority=(Developer ID Application:.*)/\1/p' | head -n 1)"
NOTARY_ID=""
if [[ -f "$NOTARY_SUBMISSION_ID_FILE" ]]; then
  NOTARY_ID="$(cat "$NOTARY_SUBMISSION_ID_FILE" | tr -d '[:space:]')"
fi

export APP_NAME BUNDLE_ID APP_VERSION REL_ZIP REL_MANIFEST TEAM_ID SIGNING_AUTH NOTARY_ID
python - <<'PY'
import json
import os
import pathlib
import time

manifest = {
    'app_name': os.environ['APP_NAME'],
    'bundle_id': os.environ['BUNDLE_ID'],
    'version': os.environ['APP_VERSION'],
    'build_timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'team_id': os.environ.get('TEAM_ID', ''),
    'signing_authority': os.environ.get('SIGNING_AUTH', ''),
    'notary_submission_id': os.environ.get('NOTARY_ID', ''),
    'stapled': True,
    'artifact_zip': os.path.basename(os.environ['REL_ZIP']),
}
pathlib.Path(os.environ['REL_MANIFEST']).write_text(json.dumps(manifest, indent=2) + '\n')
print(f"[release] Wrote manifest: {os.environ['REL_MANIFEST']}")
PY

echo "[release] Creating final zip: $REL_ZIP"
rm -f "$REL_ZIP"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$REL_ZIP"
ls -lh "$REL_ZIP"
echo "[release] Done."
