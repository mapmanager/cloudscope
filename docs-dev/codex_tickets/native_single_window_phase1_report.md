# Native single-window Phase 1 — spawn window args and cleanup

## Files changed

- `src/cloudscope/desktop/single_window_native.py` (new)
- `src/cloudscope/app.py`
- `src/cloudscope/pages/home_page.py`
- `tests/cloudscope/test_single_window_native.py` (new)
- `docs-dev/codex_tickets/native_single_window_phase0_diag_report.md` (prior)
- `docs-dev/codex_tickets/native_single_window_phase1_report.md` (this file)

## Summary of implementation

Phase 0 showed geometry tracking, splitter capture, and shutdown save already work.
The remaining bugs were:

1. **Launch geometry / `confirm_close` not applied** — NiceGUI starts pywebview in a
   `spawn` child that does not inherit parent `app.native.window_args`.
2. **Quit dialog missing** — same root cause (`confirm_close` never reached the child window).

**Fix (KISS):**

- `configure_native_window()` exports window kwargs to `CLOUDSCOPE_NATIVE_WINDOW_ARGS`
  and installs a one-time wrap of NiceGUI `_open_window` so the child merges env args
  before `webview.create_window()`.
- Pass `window_size=(w, h)` via existing `ui.run(window_size=...)` API (reaches child
  through `activate()` process args).
- Removed Phase 0 `[native-diag]` logging; kept existing move/resize/shutdown handlers.

Option C (`desktop_launcher.py`) unchanged.

## Tests added or modified

- `tests/cloudscope/test_single_window_native.py` — env roundtrip and spawn patch wrapper

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_single_window_native.py tests/cloudscope/test_home_page_right_pool_panel.py -q
```

## Test results

4 passed

## Manual verification (maintainer)

1. `uv run python src/cloudscope/app.py`
2. Move/resize window, drag file-list splitter, quit with red close → confirm dialog
3. Relaunch → window opens at saved geometry
4. Repeat quit with Cmd+Q → confirm dialog

## Concerns or follow-ups

- If packaged macOS app still fails, confirm `cloudscope` is importable when the spawn
  child unpickles the wrapped `_open_window` target.
- Consider upstream NiceGUI issue for native `window_args` under `spawn` (optional).
- `ag-grid-community` ESM 404 is unrelated; track separately.
