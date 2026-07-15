#!/usr/bin/env bash
# Local-only secrets for signing + notarization.
#
# Copy this file to _secrets.sh and edit:
#   cp packaging/acqstore_server/_secrets.example.sh packaging/acqstore_server/_secrets.sh
#   chmod 600 packaging/acqstore_server/_secrets.sh
#
# You can reuse the same Developer ID / notarytool profile as CloudScope
# (packaging/macos/_secrets.sh) — only the .app / bundle id differ.
#
# Do not commit _secrets.sh.

export SIGN_ID='Developer ID Application: <YOUR_NAME> (<TEAM_ID>)'

# Name you used with:
#   xcrun notarytool store-credentials <PROFILE_NAME> \
#     --apple-id <APPLE_ID> \
#     --team-id <TEAM_ID> \
#     --password <APP_SPECIFIC_PASSWORD>
export NOTARY_PROFILE='<YOUR_NOTARYTOOL_PROFILE_NAME>'
