# 018 — Debug view for disconnect/reconnect and state read-out

## Summary

Added a new left-toolbar **Debug** tab (icon `bug_report`) hosting a
`DebugView`. The view provides:

- **Disconnect** button → `ui.run_javascript("socket.io.engine.close();")`
- **Reconnect** button → `ui.run_javascript("socket.io.engine.connect();")`
- **Refresh** button + a read-only, monospaced `ui.label` showing the currently
  stored, Python-serializable app state as indented JSON.

This is a developer aid for exercising the client disconnect/reconnect (and
desktop sleep/wake) restore path and inspecting what state exists at each phase.
It does **not** change where or how state is stored.

## Where app state is stored today (analysis, not changed)

CloudScope keeps live per-session state in its own `CloudScopeRuntime` object,
held in a process-global `CloudScopeRuntimeRegistry` keyed by
`user_context.user_id` (`src/cloudscope/runtime.py`). Specifically:

- Live UI state: `runtime.home_page_controller.state` (`HomePageState`) —
  `selection` (`PrimarySelection`), `primary_x_range`, `file_ids`,
  `acq_image_list`.
- Reconnect chrome snapshot: `runtime.session_snapshot`
  (`HomePageSessionSnapshot`), captured on client disconnect.

This is **plain in-memory Python, not NiceGUI `app.storage.*`**. The only
NiceGUI storage used anywhere is `app.storage.browser` for the demo session id.

Per the NiceGUI storage API (https://nicegui.io/documentation/storage):

- Our custom registry is closest in scope to `app.storage.user`/`app.storage.general`
  (stable per-user, server-side), and it is **correct for disconnect/reconnect
  and sleep/wake while the server process stays alive** — which is the current
  requirement. The stable runtime key survives websocket reconnects.
- It is **not durable across a server/process restart** the way persisted
  `app.storage.user` / `app.storage.general` are (those write to disk). If
  restart durability is later required, that is a separate, deliberate change —
  out of scope here and intentionally not made.

The debug view reports the serializable subset (selection, x-range, file count,
whether an image list is loaded, and the snapshot chrome + per-view blob keys).
`acq_image_list` and `visible_file_ids_provider` are intentionally not
serialized (backend object / callable).

## Files changed

- `src/cloudscope/views/view_ids.py` — added `ViewId.DEBUG`.
- `src/cloudscope/views/debug_view.py` — new `DebugView`.
- `src/cloudscope/views/left_toolbar_view.py` — import, tab entry, construct,
  build, and register the debug view.
- `tests/cloudscope/test_left_toolbar_view.py` — updated `panel_view_ids`
  assertion and added a `DebugView` construction check.
- `tests/cloudscope/test_debug_view.py` — new tests for state collection and
  JSON rendering.

## Tests added or modified

- `tests/cloudscope/test_debug_view.py` (new): view id, collect-state with and
  without a snapshot, valid-JSON rendering, and graceful handling when the
  runtime is unavailable.
- `tests/cloudscope/test_left_toolbar_view.py`: added Debug tab to the expected
  `panel_view_ids` tuple and a `DebugView` instance assertion.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_debug_view.py tests/cloudscope/test_left_toolbar_view.py -q
```

## Test results

9 passed.

## Concerns / follow-ups

- The disconnect/reconnect JS uses `socket.io.engine.close()` /
  `socket.io.engine.connect()` per the user-provided recipe; verify live in the
  native desktop app.
- Making state durable across process restart (persisted NiceGUI storage) is a
  deliberate future decision, intentionally not addressed here.
