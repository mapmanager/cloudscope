#!/usr/bin/env bash
# Submit the pre-notarization zip to Apple notary service.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_config.sh"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_secrets.sh"

if [[ ! -f "$PRE_NOTARIZE_ZIP" ]]; then
  echo "ERROR: Zip not found: $PRE_NOTARIZE_ZIP" >&2
  exit 2
fi

echo "[notary] Submitting: $PRE_NOTARIZE_ZIP"
echo "[notary] Profile   : $NOTARY_PROFILE"
OUT="$(xcrun notarytool submit "$PRE_NOTARIZE_ZIP" --keychain-profile "$NOTARY_PROFILE" 2>&1 || true)"
echo "$OUT"

SUB_ID="$(echo "$OUT" | sed -nE 's/^[[:space:]]*id:[[:space:]]*([0-9A-Fa-f-]+).*/\1/p' | head -1)"
if [[ -z "$SUB_ID" ]]; then
  echo "ERROR: could not parse notary submission id." >&2
  exit 1
fi

mkdir -p "$(dirname "$NOTARY_SUBMISSION_ID_FILE")"
echo "$SUB_ID" > "$NOTARY_SUBMISSION_ID_FILE"
echo "[notary] Saved submission id: $NOTARY_SUBMISSION_ID_FILE"
