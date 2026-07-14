# 028 — Docker/Oracle web deploy build-info stamp

## Problem

Packaged macOS and Windows apps stamp `src/cloudscope/_build_info.py` so App
Info shows commit/version identity. Docker / Oracle web deploys used
`docker compose up --build -d cloudscope` without that stamp, so App Info fell
back to development/`unknown` values. `.git` is dockerignored, so in-image git
alone cannot invent identity.

## Goals

1. Host-side stamp (Python 3.10+ stdlib) compatible with Oracle (`python3` 3.10,
   no `uv` required).
2. Thin deploy wrapper under `packaging/` that stamps, builds, and cleans up.
3. Dockerfile hard-fail when the stamp file is missing before image build.
4. Keep macOS / Windows packaging paths unchanged in this ticket.

## Files changed

- `packaging/write_build_info.py` — shared host stamp writer (`BUILD_INFO` schema)
- `packaging/deploy_cloudscope_web.sh` — stamp → `docker compose up --build -d
  cloudscope` → remove host `_build_info.py`
- `Dockerfile` — require stamp after `COPY src`; update usage comments
- `docker-compose.yml` — document preferred deploy wrapper / stamp flow
- `tests/packaging/__init__.py` — empty package marker
- `tests/packaging/test_write_build_info.py` — writer/schema/version tests
- `docs-dev/cursor_tickets/028_docker_web_build_info_stamp_report.md` — this report

## Summary of implementation

- `write_build_info.py` parses `pyproject.toml` version with regex (no
  `tomllib`), gathers git identity via subprocess, optional package versions when
  importable, and writes the same `BUILD_INFO` keys as macOS/Windows.
- `deploy_cloudscope_web.sh` fail-fast checks for `python3`, `git`, and
  `docker compose`, stamps, deploys `cloudscope`, and always cleans the host
  transient module via `EXIT` trap.
- Dockerfile `RUN test -f src/cloudscope/_build_info.py` fails builds that skip
  the stamp (forces wrapper / explicit `write_build_info.py`).

## Tests added or modified

- `tests/packaging/test_write_build_info.py`

## Exact test commands run

```bash
python3 packaging/write_build_info.py --output /tmp/cloudscope_build_info_smoke.py
uv run pytest tests/packaging/test_write_build_info.py tests/cloudscope/test_build_info.py -q
```

## Test results

- Writer smoke: **OK** (version `0.1.3`, full key set)
- `uv run pytest tests/packaging/test_write_build_info.py tests/cloudscope/test_build_info.py -q`: **6 passed**

## Concerns or follow-ups

- `cloudscope-dev` uses the same Dockerfile, so image build still requires a
  stamp; the `./src` bind mount can then shadow it at runtime (documented in
  compose comments).
- Optional later DRY: point macOS `build_info.sh` and Windows CI at
  `packaging/write_build_info.py`.
- Full `docker compose build` not run in this ticket; verify on macOS/Oracle with
  `./packaging/deploy_cloudscope_web.sh` and App Info in the browser.
