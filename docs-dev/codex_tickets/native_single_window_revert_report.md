# Native single-window revert — KISS geometry restore

## Files changed

- `src/cloudscope/app.py`
- `src/cloudscope/pages/home_page.py`
- `src/cloudscope/desktop/single_window_native.py` (deleted)
- `tests/cloudscope/test_single_window_native.py` (deleted)
- `docs-dev/codex_tickets/native_single_window_revert_report.md`

## Summary of implementation

Reverted the spawn monkeypatch / env-export approach (crashed on macOS
``spawn`` pickling). Restored the original NiceGUI pattern:

1. **Before ``ui.run()``** — ``configure_native_window()`` updates
   ``app.native.window_args`` (``x``, ``y``, ``width``, ``height``,
   ``confirm_close``). No ``ui.run(window_size=...)``.

2. **On first native ``loaded``** — ``home_page`` applies saved rect via
   ``app.native.main_window.move()`` and ``set_window_size()`` (spawn-safe
   restore through NiceGUI ``WindowProxy``).

3. **Unchanged** — ``moved``/``resized`` handlers and shutdown
   ``app_config.save()`` (already working per Phase 0).

``confirm_close`` remains in ``window_args`` for when the child sees them;
quit dialog deferred pending minimal child-side fix.

Option C unchanged.

## Tests added or modified

None (revert + small ``home_page`` hook).

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_home_page_right_pool_panel.py -q
```

## Test results

```
uv run pytest tests/cloudscope/test_home_page_right_pool_panel.py -q
.                                                                        [100%]
1 passed in 1.60s
```

## Manual verification

1. ``uv run python src/cloudscope/app.py`` — must start without traceback
2. Move/resize window, quit, relaunch — visual geometry matches saved rect
3. Splitters still persist on quit (unchanged)

## Concerns or follow-ups

- ``confirm_close`` / quit yes-no dialog may still be absent under spawn until
  ``window_args`` reach the pywebview child at ``create_window`` time.
