#!/usr/bin/env bash
# Regenerate platform packaging icons from the master PNG.
#
# Source of truth:
#   packaging/assets/CloudScope.png  (1024x1024 recommended)
#
# Outputs (committed alongside the master):
#   packaging/assets/CloudScope.icns  (macOS nicegui-pack / PyInstaller)
#   packaging/assets/CloudScope.ico   (Windows nicegui-pack / PyInstaller)
#
# Requires: macOS (iconutil), uv, Pillow (project dependency).
#
# Usage (from repo root):
#   ./packaging/assets/build_icons.sh
#
# You do NOT need to run this for normal builds if .icns/.ico are already
# committed. Run it only when CloudScope.png changes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MASTER="$SCRIPT_DIR/CloudScope.png"
ICNS_OUT="$SCRIPT_DIR/CloudScope.icns"
ICO_OUT="$SCRIPT_DIR/CloudScope.ico"

if [[ ! -f "$MASTER" ]]; then
  echo "ERROR: master PNG not found: $MASTER" >&2
  exit 2
fi
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: building .icns requires macOS iconutil." >&2
  exit 2
fi
if ! command -v iconutil >/dev/null 2>&1; then
  echo "ERROR: iconutil not found on PATH." >&2
  exit 2
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv not found on PATH." >&2
  exit 2
fi

ICONSET="$(mktemp -d "${TMPDIR:-/tmp}/CloudScopeXXXX").iconset"
mkdir -p "$ICONSET"
trap 'rm -rf "$ICONSET"' EXIT

echo "[icons] Master: $MASTER"
echo "[icons] Iconset: $ICONSET"

cd "$REPO_ROOT"
export MASTER ICONSET ICO_OUT
uv run python <<'PY'
from pathlib import Path
import os

from PIL import Image

master = Path(os.environ["MASTER"])
icns_dir = Path(os.environ["ICONSET"])
ico_out = Path(os.environ["ICO_OUT"])

img = Image.open(master).convert("RGBA")
if img.size != (1024, 1024):
    print(f"[icons] WARNING: master is {img.size}, expected 1024x1024")

# Apple iconset pixel sizes -> required filenames
specs = [
    (16, "icon_16x16.png"),
    (32, "icon_16x16@2x.png"),
    (32, "icon_32x32.png"),
    (64, "icon_32x32@2x.png"),
    (128, "icon_128x128.png"),
    (256, "icon_128x128@2x.png"),
    (256, "icon_256x256.png"),
    (512, "icon_256x256@2x.png"),
    (512, "icon_512x512.png"),
    (1024, "icon_512x512@2x.png"),
]
for px, name in specs:
    img.resize((px, px), Image.Resampling.LANCZOS).save(icns_dir / name)
    print(f"[icons] iconset {name} ({px}x{px})")

sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save(ico_out, format="ICO", sizes=sizes)
print(f"[icons] wrote {ico_out}")
PY

iconutil -c icns "$ICONSET" -o "$ICNS_OUT"
echo "[icons] wrote $ICNS_OUT"
echo "[icons] Done."
