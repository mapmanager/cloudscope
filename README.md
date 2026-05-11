# CloudScope

[![Tests](https://github.com/mapmanager/cloudscope/actions/workflows/tests.yml/badge.svg)](https://github.com/mapmanager/cloudscope/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/mapmanager/cloudscope/branch/main/graph/badge.svg)](https://codecov.io/gh/mapmanager/cloudscope)

CloudScope is a thin NiceGUI frontend for viewing, annotating, and analyzing acquisition-backed microscopy files.

## Local development

Run the app locally in native mode:

```bash
uv run python src/cloudscope/app.py
```

Run the app locally in browser/web mode:

```bash
CLOUDSCOPE_NATIVE=0 uv run python src/cloudscope/app.py
```

Run tests with coverage and inspect missing lines:

```bash
uv run pytest \
  --cov=src/cloudscope \
  --cov=src/acqstore \
  --cov=src/nicewidgets \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-report=xml
open htmlcov/index.html
```

Run ruff locally:

```bash
uv run ruff check .
```

Ruff is intentionally not enforced in GitHub Actions yet.

## Docker

Build and run locally:

```bash
docker build -t cloudscope:latest .
docker run --rm -p 8080:8080 cloudscope:latest
```

Then open <http://localhost:8080>.

Run with Docker Compose:

```bash
docker compose up --build cloudscope
```

For server-side files, mount a folder such as `./data:/data` and load files from `/data` inside the CloudScope UI.

## Runtime environment variables

| Variable | Purpose |
| --- | --- |
| `CLOUDSCOPE_REMOTE` | Set to `1` on remote/server deployments. |
| `CLOUDSCOPE_NATIVE` | Set to `0` for browser/server mode. Defaults to native mode locally. |
| `CLOUDSCOPE_RELOAD` | Set to `1` to enable NiceGUI reload mode. |
| `CLOUDSCOPE_HOST` | Explicit NiceGUI host. Remote default is `0.0.0.0`. |
| `CLOUDSCOPE_PORT` | Explicit NiceGUI port. |
| `PORT` | Platform-provided port, preferred over `CLOUDSCOPE_PORT`. |
| `CLOUDSCOPE_STORAGE_SECRET` | NiceGUI storage secret. |
