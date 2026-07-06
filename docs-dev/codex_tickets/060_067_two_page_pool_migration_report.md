# Tickets 060–067: Two-page pool migration

## Files changed

### Created
- `src/cloudscope/runtime.py`
- `src/cloudscope/pages/pool_page.py`
- `src/cloudscope/desktop_launcher.py`
- `tests/cloudscope/test_runtime.py`
- `tests/cloudscope/test_pool_page.py`
- `tests/cloudscope/test_desktop_launcher.py`

### Modified
- `src/cloudscope/user_context.py` — `get_or_create_demo_session_id()`
- `src/cloudscope/pages/home_page.py` — runtime wiring, disconnect cleanup, hide embedded pool
- `src/cloudscope/views/velocity_pool_view.py` — client-safe refresh, dispose on hide
- `src/cloudscope/views/header_view.py` — Open Pool / Open Main buttons
- `src/cloudscope/app.py` — register `/pool`, Option C opt-in
- `tests/cloudscope/test_velocity_pool_view.py`
- `tests/cloudscope/test_home_page.py`
- `tests/cloudscope/test_app_config.py` — caplog level for warning assertion

## Summary

Implemented the full two-page CloudScope migration on branch `feature/two-page-pool`:

| Ticket | Delivered |
|--------|-----------|
| 060 | `CloudScopeRuntime`, thread-safe registry, `get_current_runtime()`, home uses shared runtime |
| 061 | `initialize_once()` / `ensure_controllers_bound()`, bootstrap moved out of `HomePage.build()` |
| 062 | `/pool` route via `pool_page.py` |
| 063 | `VelocityPoolView` `safe_invoke` pattern, `_disposed` guard, disconnect `on_hide` on Home and pool |
| 064 | Open Pool button in header (`window.open('/pool', 'cloudscope_pool')`) |
| 065 | `SHOW_EMBEDDED_VELOCITY_POOL = False` |
| 066 | `desktop_launcher.py`, `CLOUDSCOPE_MULTI_WINDOW=1` opt-in |
| 067 | Automated tests + this report |

Reload safety: runtime owns canonical `AcqImageList` / controllers; page rebuild does not create fresh `EventBus`. Registry is not cleared on client disconnect.

## Tests added or modified

- `tests/cloudscope/test_runtime.py` (new)
- `tests/cloudscope/test_pool_page.py` (new)
- `tests/cloudscope/test_desktop_launcher.py` (new)
- `tests/cloudscope/test_velocity_pool_view.py` (dispose / on_hide)
- `tests/cloudscope/test_home_page.py` (infer_load_kind from runtime)

## Test commands run

```bash
uv run pytest
uv run pytest tests/cloudscope/test_runtime.py tests/cloudscope/test_pool_page.py tests/cloudscope/test_velocity_pool_view.py
```

## Test results

```
1133 passed, 2 skipped, 13 warnings
```

## Manual tests (operator)

Manual Tests A–E from v5 should be run in browser before merge:

- A: unsaved edit survives `/` refresh
- B: unsaved edit survives `/pool` refresh
- C: `/` refresh while `/pool` open
- D: close/reopen `/pool`
- E: separate browser sessions isolated

Option C desktop: `CLOUDSCOPE_MULTI_WINDOW=1 uv run cloudscope` (verify two windows).

## Concerns / follow-ups

- Window rect persistence in Option C not fully implemented (`app.native.on` replacement deferred).
- Refresh during active `TaskRunner` task may break progress UI (documented limitation).
- `/dev/mvc` telemetry still global, not per-runtime.
- Cloudflare tunnel session isolation: verify manually (Test E in deployed environment).
