# 022 — Disconnect/reconnect stabilization cleanup

## Summary

This ticket stabilizes and clarifies the preliminary CloudScope
client-disconnect/runtime-rebuild implementation without changing its supported
scope or restore architecture.

The existing behavior remains intentionally limited to a surviving Python
process and runtime registry. Temporary browser/network disconnects, page
reloads, and native desktop sleep/wake rebuilds are supported when they resolve
to the same in-memory runtime. Server restart recovery, multi-worker runtime
sharing, independent multi-tab workspaces, and shareable URLs remain out of
scope.

## Changes

- Reused the already-resolved `CloudScopeRuntime` inside the home-page client
  disconnect closure instead of resolving the runtime again during teardown.
- Protected `reconnect_build_in_progress` with `try/finally` so build or restore
  failures cannot leave normal view hydration permanently suppressed.
- Renamed the local `was_initialized` concept to `is_runtime_rebuild` and
  documented that this includes reconnect, page reload, or another page build
  against an existing runtime.
- Simplified `BaseView._should_suppress_reconnect_hydrate()`:
  - removed the silent `ImportError` fallback;
  - removed the redundant `bool(...)` conversion;
  - returned the typed runtime flag directly.
- Expanded lifecycle diagnostics to log NiceGUI client id, runtime key, user
  context kind/id, and snapshot presence.
- Documented `session_snapshot` as an in-memory, same-process, latest-writer-wins
  snapshot when multiple clients share one runtime.
- Strengthened reconnect tests:
  - the reconnect event is checked against the typed restorable app-state
    projection;
  - repeated view show/hide cycles are checked for subscription accumulation.

## Supported boundary

```text
temporary remote disconnect  supported on the same process/runtime
server/process restart       not supported
multi-worker deployment      not supported safely
multiple tabs                may share one runtime; one tab is preferred
```

## Files changed

- `src/cloudscope/pages/home_page.py`
- `src/cloudscope/views/base_view.py`
- `src/cloudscope/runtime.py`
- `tests/cloudscope/test_base_view.py`
- `tests/cloudscope/test_controller.py`
- `docs-dev/cloudscope/dev-roadmap-reconnect.md`
- `docs-dev/cursor_tickets/022_reconnect_stabilization_cleanup_report.md`

## Out of scope

- `app.storage.user` persistence
- server restart recovery
- multi-worker synchronization
- independent per-tab runtimes
- runtime registry key changes
- shareable snapshot links or `share_id`
- adding typed reconnect state to views without a demonstrated requirement
- rewriting build-time/post-build restore architecture


## Verification

Static verification completed:

```bash
python -m compileall -q \
  src/cloudscope/pages/home_page.py \
  src/cloudscope/views/base_view.py \
  src/cloudscope/runtime.py \
  tests/cloudscope/test_base_view.py \
  tests/cloudscope/test_controller.py
```

The focused pytest command was attempted, but the isolated execution container
could not complete the project's `uv` dependency resolution. The system Python
also lacks project dependencies such as NiceGUI and `czifile`. Therefore pytest
results are intentionally not claimed in this report. Run the focused tests in
the normal CloudScope development environment after applying the replacement
files.

Recommended focused command:

```bash
uv run pytest \
  tests/cloudscope/test_base_view.py \
  tests/cloudscope/test_controller.py \
  tests/cloudscope/test_runtime.py \
  tests/cloudscope/test_session_state.py \
  tests/cloudscope/test_home_page.py \
  tests/cloudscope/test_home_page_build.py -q
```

Manual verification should repeat the existing Debug View disconnect/reconnect
workflow in `./scripts/run app`.
