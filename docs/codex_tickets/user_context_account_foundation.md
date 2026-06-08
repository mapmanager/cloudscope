# User Context / Account Foundation Ticket

## Purpose

Add a small user/workspace boundary for CloudScope so desktop/native use remains
automatic while remote/cloud use can isolate public demo sessions and future
authenticated users.

## Implemented behavior

- Local/native use resolves `UserContextKind.LOCAL_OS_USER` and continues to use
  platformdirs-derived config/data/cache paths.
- Remote unauthenticated use resolves `UserContextKind.SERVER_DEMO`.
- Demo contexts use fresh non-persistent `AppConfig` defaults for each page
  construction.
- Demo uploads are allowed, but are stored in a disposable per-browser-session
  directory under `CLOUDSCOPE_DATA_DIR/tmp/demo-sessions/<session_id>/uploads`.
- Demo sessions use a `.last_used` marker. Expired demo session directories are
  deleted when a new demo context is resolved.
- Demo upload storage is checked before copy against both a per-upload limit and
  a total per-session quota.
- Future authenticated users are represented by `UserContextKind.SERVER_AUTH_USER`
  and map to `CLOUDSCOPE_DATA_DIR/users/<safe_user_id>/`.
- Load sample data now receives `user_context.sample_data_dir`.
- Upload storage now receives `user_context.upload_dir` and checks
  `user_context.quota` before copying.
- Docker Compose now defines `CLOUDSCOPE_DATA_DIR=/data`, bind-mounts `./data:/data`,
  and sets explicit demo quota/cleanup environment variables.

## Demo storage defaults

The default remote/demo limits are centralized in `src/cloudscope/user_context.py`
and can be overridden via environment variables:

- `CLOUDSCOPE_DEMO_SESSION_QUOTA_MB`, default `500`
- `CLOUDSCOPE_DEMO_MAX_UPLOAD_MB`, default `250`
- `CLOUDSCOPE_DEMO_MAX_SESSION_AGE_HOURS`, default `24`

Docker Compose sets those values explicitly for both `cloudscope` and
`cloudscope-dev`.

## New files

- `src/cloudscope/user_context.py`
  - Defines `UserContext`, `UserContextKind`, path resolution, demo/auth/local
    context construction, safe filesystem user ids, demo `.last_used` markers,
    and expired demo session cleanup.
- `src/cloudscope/quota.py`
  - Defines small directory-size and quota helpers used before uploads.
- `tests/cloudscope/test_user_context.py`
  - Covers local, demo, authenticated, environment-based context resolution, and
    expired demo cleanup.
- `tests/cloudscope/test_quota.py`
  - Covers recursive directory-size, MB conversion, per-upload limits, and total
    quota checks.
- `docs/codex_tickets/user_context_account_foundation.md`
  - This implementation note.

## Edited files

- `src/cloudscope/app_config.py`
  - Adds non-persistent `AppConfig.ephemeral()` and a `persistent` flag. Existing
    persistent behavior remains the default.
- `src/cloudscope/app.py`
  - Native window setup now loads config through a local `UserContext`.
- `src/cloudscope/pages/home_page.py`
  - Resolves `UserContext` before loading `AppConfig`, creates a browser-stable
    demo session id when NiceGUI browser storage is available, and passes the
    context to `LoadSaveController`, `LoadSaveView`, and `HomePage`.
- `src/cloudscope/controllers/load_save_controller.py`
  - Accepts optional `UserContext`; sample data loading uses
    `user_context.sample_data_dir` when present.
- `src/cloudscope/views/load_save_view.py`
  - Accepts optional `UserContext`; uploads are copied into
    `user_context.upload_dir`, checked against `user_context.quota`, and touch
    the demo `.last_used` marker after successful storage.
- `docker-compose.yml`
  - Adds `CLOUDSCOPE_DATA_DIR=/data`, sets sample data to `/data/shared/sample-data`,
    adds explicit demo quota/cleanup environment variables, and changes the bind
    mount to `./data:/data`.
- `docs/cloudscope_architecture.md`
  - Documents the user/workspace context concept and remote data-root convention.
- `tests/cloudscope/test_load_save_view.py`
  - Updates upload helper tests for explicit upload directory injection and adds
    user-context quota and max-upload coverage.
- `tests/cloudscope/test_load_save_controller.py`
  - Updates the sample-data monkeypatch signature to accept `sample_data_dir`.

## Not implemented yet

- Cloudflare Access JWT validation and identity resolution.
- In-app `/login`, registration, password storage, or password reset.
- Hard operating-system or filesystem quotas.
