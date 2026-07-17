#!/usr/bin/env bash
set -euo pipefail

REPLACEMENT_DIR="${1:-}"

if [[ -z "$REPLACEMENT_DIR" ]]; then
  echo "Usage: ./apply_mkdocs_replacements.sh /path/to/unzipped/replacement_folder"
  exit 1
fi

if [[ ! -d "$REPLACEMENT_DIR" ]]; then
  echo "ERROR: replacement dir does not exist: $REPLACEMENT_DIR"
  exit 1
fi

if [[ ! -f "pyproject.toml" || ! -d "docs" ]]; then
  echo "ERROR: run this script from the cloudscope repo root"
  exit 1
fi

if [[ ! -d "$REPLACEMENT_DIR/docs" ]]; then
  echo "ERROR: replacement dir must contain a docs/ folder"
  exit 1
fi

if [[ -n "$(git status --porcelain | grep -v '^\??')" ]]; then
  echo "ERROR: git working tree is not clean."
  echo "Commit or stash changes first."
  exit 1
fi

echo "Dry run: syncing MkDocs files under docs/ only"
echo

rsync -av --dry-run \
  "$REPLACEMENT_DIR/docs/" \
  ./docs/ \
  --include='*/' \
  --include='*.md' \
  --include='*.ipynb' \
  --include='*.css' \
  --include='*.png' \
  --include='*.svg' \
  --include='*.html' \
  --exclude='*'

echo
read -r -p "Apply these docs/ replacements? Type YES: " CONFIRM

if [[ "$CONFIRM" != "YES" ]]; then
  echo "Cancelled."
  exit 0
fi

rsync -av \
  "$REPLACEMENT_DIR/docs/" \
  ./docs/ \
  --include='*/' \
  --include='*.md' \
  --include='*.ipynb' \
  --include='*.css' \
  --include='*.png' \
  --include='*.svg' \
  --include='*.html' \
  --include='*.json' \
  --exclude='*'

echo
echo "Applied MkDocs docs/ replacements."
echo "Review with:"
echo "  git status"
echo "  git diff"