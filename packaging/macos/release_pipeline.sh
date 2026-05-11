#!/usr/bin/env bash
# Full release pipeline: branch + tag + build + sign + notarize + staple + zip.
#
# Run from repo root:
#   ./packaging/macos/release_pipeline.sh
#
# Precondition:
# - You are on main.
# - pyproject.toml has the desired release version.
# - Working tree is clean, or only pyproject.toml/CHANGELOG.md have pending changes.
# - packaging/macos/_secrets.sh exists locally.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/_config.sh"

RELVER="$(grep -E '^version[[:space:]]*=' "$REPO_ROOT/pyproject.toml" 2>/dev/null | head -1 | sed -E 's/^version[[:space:]]*=[[:space:]]*["'\'' ]*([^"'\'' ]+)["'\'' ]*.*/\1/')"
RELVER="${RELVER:?ERROR: could not read version from pyproject.toml}"
RELBR="release/v${RELVER}"
RELTAG="v${RELVER}"

echo "[release] Version: $RELVER"
echo "[release] Branch : $RELBR"
echo "[release] Tag    : $RELTAG"

CURRENT_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  echo "ERROR: not on main branch (current: $CURRENT_BRANCH)." >&2
  exit 2
fi

CHANGED="$(git -C "$REPO_ROOT" diff --name-only 2>/dev/null; git -C "$REPO_ROOT" diff --cached --name-only 2>/dev/null)" || true
if [[ -n "$CHANGED" ]]; then
  BAD="$(echo "$CHANGED" | grep -vE '^(pyproject\.toml|CHANGELOG\.md)$' || true)"
  if [[ -n "$BAD" ]]; then
    echo "ERROR: working tree has changes other than pyproject.toml/CHANGELOG.md." >&2
    echo "$BAD" >&2
    exit 2
  fi
fi

if git -C "$REPO_ROOT" rev-parse "$RELTAG" >/dev/null 2>&1; then
  echo "ERROR: tag already exists: $RELTAG" >&2
  exit 2
fi
if git -C "$REPO_ROOT" rev-parse "refs/heads/$RELBR" >/dev/null 2>&1; then
  echo "ERROR: branch already exists: $RELBR" >&2
  exit 2
fi

git -C "$REPO_ROOT" checkout -b "$RELBR"
git -C "$REPO_ROOT" add pyproject.toml CHANGELOG.md 2>/dev/null || true
if ! git -C "$REPO_ROOT" diff --cached --quiet 2>/dev/null; then
  git -C "$REPO_ROOT" commit -m "Release ${RELTAG}"
else
  echo "[release] No version/changelog changes to commit."
fi

git -C "$REPO_ROOT" tag -a "$RELTAG" -m "${APP_NAME} ${RELTAG}"
git -C "$REPO_ROOT" checkout "$RELTAG"

"$SCRIPT_DIR/build_app.sh"
"$SCRIPT_DIR/codesign_and_zip.sh"
"$SCRIPT_DIR/notary_submit.sh"
"$SCRIPT_DIR/notary_poll_until_done.sh"
"$SCRIPT_DIR/staple_and_verify.sh"
"$SCRIPT_DIR/make_release_zip.sh"

git -C "$REPO_ROOT" push origin "$RELTAG"
git -C "$REPO_ROOT" push origin "$RELBR"

git -C "$REPO_ROOT" checkout main
git -C "$REPO_ROOT" pull
git -C "$REPO_ROOT" merge --no-ff "$RELBR"
git -C "$REPO_ROOT" push

REL_ZIP="$DIST_DIR/${APP_NAME}-${RELVER}-${RELEASE_PLATFORM}.zip"
REL_MANIFEST="$DIST_DIR/${APP_NAME}-${RELVER}-${RELEASE_PLATFORM}-manifest.json"
if command -v gh >/dev/null 2>&1; then
  echo "[release] Uploading artifacts to GitHub Release..."
  if gh release view "$RELTAG" >/dev/null 2>&1; then
    gh release upload "$RELTAG" "$REL_ZIP" "$REL_MANIFEST" --clobber
  else
    gh release create "$RELTAG" "$REL_ZIP" "$REL_MANIFEST" --notes "${APP_NAME} ${RELTAG}"
  fi
else
  echo "[release] gh not found; skipping GitHub Release upload."
fi

echo "[release] Done."
echo "[release] Zip     : $REL_ZIP"
echo "[release] Manifest: $REL_MANIFEST"
