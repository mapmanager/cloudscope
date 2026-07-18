#!/usr/bin/env bash
# Regenerate platform packaging icons from master PNGs.
#
# Masters (committed):
#   packaging/assets/CloudScope.png       — black CS on white
#   packaging/assets/AcqStoreServer.png   — teal AS on white
#
# Outputs (committed alongside masters):
#   *.icns  (macOS nicegui-pack / PyInstaller)
#   *.ico   (Windows nicegui-pack / PyInstaller)
#
# Requires: macOS (iconutil), uv, Pillow (project dependency).
#
# Usage (from repo root):
#   ./packaging/assets/build_icons.sh              # both apps
#   ./packaging/assets/build_icons.sh CloudScope
#   ./packaging/assets/build_icons.sh AcqStoreServer
#
# You do NOT need to run this for normal builds if .icns/.ico are already
# committed. Run it only when a master PNG changes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

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

build_one() {
  local stem="$1"
  local master="$SCRIPT_DIR/${stem}.png"
  local icns_out="$SCRIPT_DIR/${stem}.icns"
  local ico_out="$SCRIPT_DIR/${stem}.ico"

  if [[ ! -f "$master" ]]; then
    echo "ERROR: master PNG not found: $master" >&2
    exit 2
  fi

  local iconset
  iconset="$(mktemp -d "${TMPDIR:-/tmp}/${stem}XXXX").iconset"
  mkdir -p "$iconset"
  # shellcheck disable=SC2064
  trap "rm -rf '$iconset'" RETURN

  echo "[icons] Master: $master"
  echo "[icons] Iconset: $iconset"

  cd "$REPO_ROOT"
  export MASTER="$master" ICONSET="$iconset" ICO_OUT="$ico_out"
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

  iconutil -c icns "$iconset" -o "$icns_out"
  echo "[icons] wrote $icns_out"
}

TARGETS=("$@")
if [[ "${#TARGETS[@]}" -eq 0 ]]; then
  TARGETS=(CloudScope AcqStoreServer)
fi

for stem in "${TARGETS[@]}"; do
  build_one "$stem"
done

echo "[icons] Done."
