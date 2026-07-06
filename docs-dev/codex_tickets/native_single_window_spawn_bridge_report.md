# Native single-window — spawn bridge for window_args + confirm_close

## Files changed

- `src/cloudscope/app.py`
- `src/cloudscope/pages/home_page.py`
- `src/cloudscope/desktop/native_spawn.py` (new)
- `tests/cloudscope/test_native_spawn.py` (new)
- `docs-dev/codex_tickets/native_single_window_spawn_bridge_report.md`

## Summary of implementation

**Snap bug:** Window opened at NiceGUI default (800×600) then jumped on
``loaded`` because the pywebview child (macOS ``spawn``) had empty
``window_args``. Removed the ``loaded`` restore hook.

**Fix:** Before ``ui.run()``, ``configure_native_window()`` still sets
``app.native.window_args`` (``x``, ``y``, ``width``, ``height``,
``confirm_close``). A small module-level spawn bridge
(``native_spawn.py``) exports those kwargs to env and replaces
NiceGUI's ``_open_window`` with a picklable entrypoint that merges them
in the child before ``webview.create_window``. Geometry and
``confirm_close`` apply at window creation — no post-load snap, no
deprecated ``set_window_size``.

Option C unchanged.

## Tests added or modified

- `tests/cloudscope/test_native_spawn.py` (new)

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_native_spawn.py tests/cloudscope/test_home_page_right_pool_panel.py -q
```

## Test results

```
uv run pytest tests/cloudscope/test_native_spawn.py tests/cloudscope/test_home_page_right_pool_panel.py -q
.....                                                                    [100%]
5 passed in 1.42s
```

## Manual verification

1. Launch app — window appears at saved geometry (no flash/snap)
2. Close window — native yes/no quit dialog
3. Move/resize, quit, relaunch — geometry persists

## Concerns or follow-ups

None.
