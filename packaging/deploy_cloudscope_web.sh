#!/usr/bin/env bash
# Stamp build identity and deploy the CloudScope web service with Compose.
#
# Run from anywhere; the script resolves the repository root:
#   ./packaging/deploy_cloudscope_web.sh
#
# Flow:
#   1. Write src/cloudscope/_build_info.py (same schema as macOS/Windows packaging)
#   2. docker compose up --build -d cloudscope
#   3. Remove the host-side transient _build_info.py (image keeps its copy)
#
# Requires: python3 (>=3.10), git, docker compose.
# Does not require uv on the host (Oracle-friendly).
#
# Bare `docker compose up --build cloudscope` without a prior stamp will fail
# the Dockerfile presence check — use this wrapper for stamped web deploys.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_INFO_PATH="$REPO_ROOT/src/cloudscope/_build_info.py"
WRITE_BUILD_INFO_PY="$SCRIPT_DIR/write_build_info.py"

_cleanup_transient_build_info() {
  if [[ -f "$BUILD_INFO_PATH" ]]; then
    rm -f "$BUILD_INFO_PATH"
    echo "[deploy] Removed transient build info: $BUILD_INFO_PATH"
  fi
}

trap _cleanup_transient_build_info EXIT

cd "$REPO_ROOT"

echo "[deploy] Repo root: $REPO_ROOT"

if [[ ! -f "$WRITE_BUILD_INFO_PY" ]]; then
  echo "ERROR: missing stamp script: $WRITE_BUILD_INFO_PY" >&2
  exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required on PATH (Oracle/host stamp; uv is not required)." >&2
  exit 2
fi
if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git is required on PATH to stamp commit/branch identity." >&2
  exit 2
fi
if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is required on PATH." >&2
  exit 2
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: docker compose is required (Docker Compose V2 plugin)." >&2
  exit 2
fi

echo "[deploy] python3: $(python3 -V)"
echo "[deploy] Stamping build info..."
python3 "$WRITE_BUILD_INFO_PY" --repo-root "$REPO_ROOT" --output "$BUILD_INFO_PATH"

if [[ ! -f "$BUILD_INFO_PATH" ]]; then
  echo "ERROR: stamp did not create $BUILD_INFO_PATH" >&2
  exit 3
fi

echo "[deploy] Building and starting cloudscope service..."
docker compose up --build -d cloudscope

echo "[deploy] Done."
echo "[deploy] App Info should show the stamped build identity in the running container."
echo "[deploy] Open the web UI (default http://localhost:8080)."
