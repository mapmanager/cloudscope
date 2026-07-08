# 003 — Native window title sync

**Status:** implemented  
**Type:** implementation ticket

---

## Summary

When CloudScope runs in NiceGUI single-window native mode, the OS desktop window title now tracks the currently loaded file, folder, or CSV. The title uses `AppConfig.last_path` (same source as the hamburger menu check mark) and updates after successful loads and on home-page reconnect.

Title format: `CloudScope — ~/path/to/source` (or `CloudScope` when nothing is loaded).

`ui.run()` and Option C multi-window desktop were not modified.

---

## Files changed

| File | Change |
|------|--------|
| `src/cloudscope/utils/utils.py` | Added `_path_display`, `_format_native_window_title`, `set_native_main_window_title` |
| `src/cloudscope/views/load_save_view.py` | Import shared `_path_display` from utils |
| `src/cloudscope/controllers/load_save_controller.py` | Call `set_native_main_window_title` after `set_last_path` |
| `src/cloudscope/pages/home_page.py` | Sync title on page build (reconnect) |
| `tests/cloudscope/test_utils.py` | New tests for path display and native title helpers |
| `tests/cloudscope/test_load_save_view.py` | Removed duplicate `_path_display` tests; import cleanup |

---

## Implementation notes

- Runtime API: `app.native.main_window.set_title(...)` via NiceGUI `WindowProxy` (single-window native only).
- `_format_native_window_title` is private; only `set_native_main_window_title` is public.
- No new module file; helpers live in existing `utils/utils.py`.

---

## Tests added or modified

- `tests/cloudscope/test_utils.py` (new)
- `tests/cloudscope/test_load_save_view.py` (moved path-display coverage to `test_utils.py`)

---

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_utils.py tests/cloudscope/test_load_save_view.py tests/cloudscope/test_load_save_controller.py -q
```

---

## Test results

77 passed in 1.73s

---

## Concerns or follow-ups

- If a future NiceGUI version makes `WindowProxy.title` assignment work, we could switch from `set_title` to `.title` without changing call sites.
- Sample/preset loads show the real stored path; friendly labels can be added later if desired.
- Option C main-window title sync remains out of scope.
