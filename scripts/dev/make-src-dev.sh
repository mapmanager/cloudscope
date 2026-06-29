#!/usr/bin/env bash
set -euo pipefail

ZIP_NAME="${1:?Usage: make_source_zip.sh output.zip}"

zip -r "$ZIP_NAME" \
    src tests docs-dev scripts pyproject.toml README.md \
    -x \
    "*/__pycache__/*" \
    "*.pyc" \
    "*.pyo" \
    ".pytest_cache/*" \
    ".mypy_cache/*" \
    ".ruff_cache/*" \
    ".DS_Store" \
    ".ipynb_checkpoints/*" \
    "docs/site/*" \
    "site/*" \
    "build/*" \
    "dist/*" \
    ".venv/*" \
    ".git/*" \
    "*.svg" \
    "*.png" \
    "*.jpg" \
    "*.jpeg" \
    "*.tif" \
    "*.tiff" \
    "*.oir" \
    "*.czi" \
    "*.zarr/*"
