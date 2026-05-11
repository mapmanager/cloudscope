#!/usr/bin/env bash
# Poll Apple notary service until the submission is Accepted or fails.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_config.sh"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_secrets.sh"

SUB_ID="${1:-}"
if [[ -z "$SUB_ID" && -f "$NOTARY_SUBMISSION_ID_FILE" ]]; then
  SUB_ID="$(cat "$NOTARY_SUBMISSION_ID_FILE" | tr -d '[:space:]')"
fi
if [[ -z "$SUB_ID" ]]; then
  echo "ERROR: no notary submission id provided and none found at $NOTARY_SUBMISSION_ID_FILE" >&2
  exit 2
fi

echo "[poll] Submission id: $SUB_ID"
while true; do
  OUT="$(xcrun notarytool info "$SUB_ID" --keychain-profile "$NOTARY_PROFILE" 2>&1 || true)"
  echo "$OUT"
  STATUS="$(echo "$OUT" | sed -nE 's/^[[:space:]]*status:[[:space:]]*(.*)/\1/p' | head -1 | tr -d '\r')"

  if [[ "$STATUS" == "Accepted" ]]; then
    echo "[poll] ✅ Accepted"
    exit 0
  fi
  if [[ "$STATUS" == "Invalid" || "$STATUS" == "Rejected" ]]; then
    echo "[poll] ❌ $STATUS"
    echo "[poll] Fetching log..."
    xcrun notarytool log "$SUB_ID" --keychain-profile "$NOTARY_PROFILE" || true
    exit 1
  fi

  sleep 20
done
