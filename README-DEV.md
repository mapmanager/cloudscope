# zip a folder of py and md files

acqstore

zip -r cloudscope_20260614_v3.zip \
    src tests docs-dev scripts pyproject.toml \
    -x "*/__pycache__/*" \
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

find packaging \
    -type d \( -name build -o -name dist \) -prune -o \
    -type f \( \
        -name "*.md" -o \
        -name "*.sh" -o \
        -name "*.icns" -o \
        -name "*.spec" -o \
        -name "*.entitlements" -o \
        -name "*.plist" \
    \) -print | zip cloudscope_packaging_20260610_v1.zip -@
        
find docs -type f \( \
    -name "*.md" -o \
    -name "*.ipynb" -o \
    -name "*.css" -o \
    -name "*.png" -o \
    -name "*.svg" \
\) -print | zip cloudscope_docs_20260611_v1.zip -@

find tests -type f \( \
    -name "*.py" -o \
    -name "*.md" -o \
    -name "*.ipynb" -o \
    -name "*.css" -o \
    -name "*.png" -o \
    -name "*.svg" \
\) -print | zip cloudscope_tests_20260612_v1.zip -@

find docs-dev -type f \( \
    -name "*.md" -o \
    -name "*.ipynb" -o \
    -name "*.css" -o \
    -name "*.png" -o \
    -name "*.svg" \
\) -print | zip cloudscope_docs_dev_20260612_v1.zip -@

find src -type f \( \
    -name "*.py" -o \
    -name "*.md" -o \
    -name "*.ipynb" -o \
    -name "*.css" -o \
    -name "*.png" -o \
    -name "*.svg" \
\) -print | zip cloudscope_src_20260612_v1.zip -@

find .github/workflows -type f \( \
    -name "*.py" -o \
    -name "*.md" -o \
    -name "*.ipynb" -o \
    -name "*.css" -o \
    -name "*.png" -o \
    -name "*.svg" \
    -name "*.yml" \
\) -print | zip cloudscope_workflows_20260611_v1.zip -@

    zip -r cloudscope_src_20260513_v1.zip src/cloudscope -i '*.py' '*.md'

    zip -r cloudscope_src_20260609_v1.zip src/acqstore -i '*.py' '*.md'
    zip -r cloudscope_tests_20260607_v1.zip tests -i '*.py' '*.md'
    zip -r cloudscope_docs_20260607_v1.zip docs -i '*.py' '*.md'
    zip -r cloudscope_scripts_20260607_v1.zip scripts -i '*.py' '*.md'

    zip -r cloudscope_scripts_20260525_v6.zip scripts -i '*.py' '*.md'
    zip -r cloudscope_sandbox_20260525_v6.zip sandbox -i '*.py' '*.md'
    
    zip -r cloudscope_src_20260524_v6.zip src -i '*.py' '*.md'

    zip -r kymflow_20260520_diameter_v1.zip /Users/cudmore/Sites/kymflow_outer/kymflow/src/kymflow/core/analysis/diameter_analysis -i '*.py' '*.md'

    /Users/cudmore/Sites/kymflow_outer/kymflow/src/kymflow/core/analysis/diameter_analysis


# Running `src/cloudscope/app.py`

`src/cloudscope/app.py` reads its runtime configuration from environment variables (see `get_run_config_from_env` in that file). Set the variables on the same command line that launches `uv run`.

## Native (default on local machine)

```bash
uv run python src/cloudscope/app.py
```

`CLOUDSCOPE_NATIVE` defaults to `true` when `CLOUDSCOPE_REMOTE` is unset, so this opens the pywebview native window.

## Browser mode (native disabled)

```bash
CLOUDSCOPE_NATIVE=false uv run python src/cloudscope/app.py
```

NiceGUI starts a local server and opens (or lets you open) a browser tab. Add `CLOUDSCOPE_PORT` to pin the port:

```bash
CLOUDSCOPE_NATIVE=false CLOUDSCOPE_PORT=8080 uv run python src/cloudscope/app.py
```

## Remote / server mode (e.g. Oracle Cloud)

```bash
CLOUDSCOPE_REMOTE=true uv run python src/cloudscope/app.py
```

`CLOUDSCOPE_REMOTE=true` flips the defaults to `native=false`, `host=0.0.0.0`, and `port=8080`. Override any of them explicitly when needed:

```bash
CLOUDSCOPE_REMOTE=true CLOUDSCOPE_HOST=0.0.0.0 CLOUDSCOPE_PORT=9000 uv run python src/cloudscope/app.py
```

## Reload mode (auto-restart on source edits)

```bash
CLOUDSCOPE_NATIVE=false CLOUDSCOPE_RELOAD=true uv run python src/cloudscope/app.py
```

## Recognized environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `CLOUDSCOPE_REMOTE` | Treat the app as running on a remote/server host. Implies `native=false` and binds to `0.0.0.0:8080` unless overridden. | `false` |
| `CLOUDSCOPE_NATIVE` | Force native (pywebview) on/off. | `true` when `CLOUDSCOPE_REMOTE` is unset, otherwise `false` |
| `CLOUDSCOPE_RELOAD` | Toggle NiceGUI reload mode. | `false` |
| `CLOUDSCOPE_HOST` | Explicit NiceGUI host. | NiceGUI default (or `0.0.0.0` when remote) |
| `CLOUDSCOPE_PORT` | Explicit NiceGUI port. | NiceGUI default (or `8080` when remote) |
| `PORT` | Platform-provided port; takes precedence over `CLOUDSCOPE_PORT`. | unset |
| `CLOUDSCOPE_STORAGE_SECRET` | NiceGUI storage secret. | `cloudscope-dev-secret` |

Boolean variables accept `1/0`, `true/false`, `yes/no`, `y/n`, `on/off` (case-insensitive). Any other value raises `ValueError` at startup.


# Running CloudScope with Docker

CloudScope ships with a `Dockerfile` and a `docker-compose.yml`. Docker Compose is the recommended way to run the server-mode app locally and on remote hosts; it bakes in all the env vars CloudScope needs (`CLOUDSCOPE_REMOTE=1`, `CLOUDSCOPE_NATIVE=0`, `CLOUDSCOPE_HOST=0.0.0.0`, `PORT=8080`) and wires up an `./example-data` volume mount.

The live demo deployed on Oracle Cloud is available at <https://cloudscope.mapmanager.net/>.

## Docker Compose (recommended)

Two services are defined in `docker-compose.yml`:

- `cloudscope` — production-like container. Mounts `./example-data` into `/data` and points `CLOUDSCOPE_SAMPLE_DATA_DIR` at `/data/sample-data`.
- `cloudscope-dev` — same image but also bind-mounts `./src` into `/app/src` so local edits are picked up inside the container.

Build and run the production-like container in the foreground:

```bash
docker compose up --build cloudscope
# then visit http://localhost:8080
```

Build and run the dev container (live `src/` mount) in the foreground:

```bash
docker compose up --build cloudscope-dev
# then visit http://localhost:8080
```

Stop and remove the containers:

```bash
docker compose down
```

## Oracle Cloud (and other remote hosts)

For long-running deployments, use detached mode with `-d` so the server keeps running after you log out of the host:

```bash
docker compose up --build -d cloudscope
```

Useful follow-ups on a remote host:

```bash
docker compose ps                  # show running services
docker compose logs -f cloudscope  # tail logs
docker compose down                # stop and remove
```

The compose file binds to `0.0.0.0:8080` inside the container and publishes it on host port `8080`. On Oracle Cloud, make sure the VCN security list / network security group allows inbound TCP `8080` (or front the container with a reverse proxy / TLS terminator that maps `443` → `8080`). The live demo at <https://cloudscope.mapmanager.net/> runs from this same compose definition behind a TLS proxy.

## Plain Docker (without Compose)

The `Dockerfile` already sets the server-mode env vars and `EXPOSE 8080`, so a manual `docker run` is straightforward:

```bash
docker build -t cloudscope:latest .
docker run --rm -p 8080:8080 cloudscope:latest
# then visit http://localhost:8080
```

Add a data mount when you want to load files from disk:

```bash
docker run --rm -p 8080:8080 -v "$PWD/example-data:/data" cloudscope:latest
```

For long-running deployments without Compose, use `-d` (detached) and a restart policy:

```bash
docker run -d --name cloudscope --restart unless-stopped -p 8080:8080 cloudscope:latest
```

Prefer `docker compose` over raw `docker run` for anything beyond a quick smoke test — it keeps the env vars, ports, and volumes consistent with the deployed configuration.


# CloudScope CI/CD and release workflow

This section is a short reminder for the local release workflow. It is intentionally small and practical.

## Normal development

Work on `main` is acceptable for solo development.

Pushes to `main` run:

- tests
- docs build/deploy

A normal development push does **not** create a GitHub Release.

## Preparing a release

Before tagging, update:

- `pyproject.toml` version, for example `version = "0.1.0"`
- `CHANGELOG.md`, moving completed notes from `[Unreleased]` into the release section

Example release section:

```md
## [0.1.0] - 2026-06-10

### Added

- Added first official release workflow.
```

## Local release sanity check

Run this before creating a tag:

```bash
uv run python scripts/check_release.py v0.1.0
```

The script checks:

- current branch is `main`
- working tree is clean
- tag format looks like `vX.Y.Z`
- local tag does not already exist
- origin tag does not already exist
- `pyproject.toml` version matches the tag
- `CHANGELOG.md` has a section for the version

## Creating and pushing a release tag

Use explicit git paths when committing release edits. Do not use `git add .`.

Example:

```bash
git add pyproject.toml CHANGELOG.md README-DEV.md scripts/check_release.py .github/workflows/release.yml .github/workflows/tests.yml .github/workflows/docs.yml
git commit -m "Prepare v0.1.0 release"

python scripts/check_release.py v0.1.0

git tag v0.1.0
git push origin main
git push origin v0.1.0
```

Pushing the tag triggers `.github/workflows/release.yml`.

## What the release workflow does

On tag pushes matching `v*.*.*`, the release workflow:

- installs Python 3.12 and uv
- validates tag/version/changelog consistency
- runs pytest
- builds MkDocs with `--strict`
- builds Python package artifacts with `uv build`
- creates a source archive from the tagged commit
- creates a zipped docs archive
- creates a GitHub Release
- uploads the package, source, and docs artifacts

## Desktop app artifacts

Windows and macOS desktop artifacts are intentionally not part of this first release workflow.

Later phases can add:

- Windows build workflow on `windows-latest`
- unsigned Windows app zip attached to releases
- macOS app zip, likely still signed/notarized locally until Apple credentials are intentionally moved into GitHub Actions secrets
