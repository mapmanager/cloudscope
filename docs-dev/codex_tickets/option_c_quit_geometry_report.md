# Option C quit geometry and save dialog

## Files changed

- `src/cloudscope/window_geometry.py`
- `src/cloudscope/desktop_launcher.py`
- `src/cloudscope/desktop/__init__.py`
- `src/cloudscope/desktop/quit_dialog.py`
- `src/cloudscope/desktop/quit_flow.py`
- `src/cloudscope/desktop/save_on_quit.py`
- `tests/cloudscope/test_window_geometry.py`
- `tests/cloudscope/test_desktop_quit_flow.py`

## Summary of implementation

- Fixed Option C quit geometry: `sync_from_window()` runs on `events.closing` while the pywebview window is still live; `persist()` now flushes in-memory `AppConfig` to disk only.
- Removed geometry read/persist from `events.closed` (cocoa deletes the window instance before `closed`, so `window.x` was `None`).
- Added `_read_live_rect()` guards for `None` geometry attrs (no traceback on shutdown).
- Replaced `confirm_close=True` with a custom quit flow: Save / Don't Save / Cancel when any loaded `AcqImage` is dirty (`AcqImageList.has_dirty_files()` / `get_dirty_files()`).
- **Save** saves all dirty files synchronously via `save_all_dirty_files_sync()`; **Cancel** returns `False` from `closing` to veto quit; **Don't Save** persists window geometry only.
- Native quit dialogs are encapsulated in `desktop/quit_dialog.py` (macOS `NSAlert`, Windows `MessageBox` Yes/No/Cancel; unsupported platforms cancel quit).
- **Fix:** `save_on_quit.get_acq_image_list()` now uses `runtime.home_page_controller` (not the nonexistent `home_controller` attribute on `CloudScopeRuntime`).

## Tests added or modified

- Modified: `tests/cloudscope/test_window_geometry.py` (persist vs sync split, `None` attrs)
- Added: `tests/cloudscope/test_desktop_quit_flow.py` (quit orchestration, save-all-dirty, dialog dispatch, runtime attribute regression)

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_window_geometry.py tests/cloudscope/test_desktop_quit_flow.py tests/cloudscope/test_desktop_launcher.py
uv run pytest
```

## Test results

- Focused: 32 passed
- Full suite: 1269 passed (after fix: re-run expected 1270)

## Concerns or follow-ups

- Manual smoke test on macOS and Windows packaged/desktop builds recommended for native quit dialogs.
- Linux desktop shows no native 3-button dialog; quit is cancelled when dirty (safe default).
- Synchronous save on the GUI thread may block briefly for large save-all operations.
- Pool window geometry still persists to disk only when main-window quit is allowed.
