#!/usr/bin/env bash
# Local-only secrets for signing + notarization.
#
# Copy this file to _secrets.sh and edit:
#   cp packaging/macos/_secrets.example.sh packaging/macos/_secrets.sh
#   chmod 600 packaging/macos/_secrets.sh
#
# Do not commit _secrets.sh.

export SIGN_ID='Developer ID Application: <YOUR_NAME> (<TEAM_ID>)'

# Name you used with:
#   xcrun notarytool store-credentials <PROFILE_NAME> \
#     --apple-id <APPLE_ID> \
#     --team-id <TEAM_ID> \
#     --password <APP_SPECIFIC_PASSWORD>
export NOTARY_PROFILE='<YOUR_NOTARYTOOL_PROFILE_NAME>'
