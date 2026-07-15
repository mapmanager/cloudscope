#!/usr/bin/env bash
# Sign → notarize → wait → staple → final zip (expects an already-built .app).
#
#   ./packaging/acqstore_server/build_app.sh
#   # smoke-test the unsigned app, then:
#   ./packaging/acqstore_server/sign_notarize_release.sh
#
# Requires packaging/acqstore_server/_secrets.sh (see _secrets.example.sh).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/codesign_and_zip.sh"
"$SCRIPT_DIR/notary_submit.sh"
"$SCRIPT_DIR/notary_poll_until_done.sh"
"$SCRIPT_DIR/staple_and_verify.sh"
"$SCRIPT_DIR/make_release_zip.sh"

echo "[pipeline] Signed, notarized, stapled release zip is under packaging/acqstore_server/dist/"
