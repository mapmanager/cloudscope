# Ticket 068: Fix Option C native desktop pickers and clipboard detection

## Files changed

- `src/cloudscope/desktop_launcher.py`
- `src/cloudscope/_py_web_view.py`
- `src/cloudscope/views/load_save_view.py`
- `src/cloudscope/views/header_view.py`
- `src/nicewidgets/utils/clipboard.py`
- `src/nicewidgets/echart_widget/widget.py`
- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
- `src/nicewidgets/tree_widget/tree_widget.py`
- `tests/cloudscope/test_py_web_view.py` (new)
- `tests/cloudscope/test_load_save_view.py`
- `tests/cloudscope/test_header_view.py`
- `tests/nicewidgets/test_clipboard_desktop.py` (new)
- `tests/nicewidgets/test_tree_widget_smoke.py`

## Summary of implementation

Option C desktop runs `ui.run(native=False)` with manual pywebview windows, so `app.native.main_window` is never set. File pickers, native-mode detection, clipboard helpers, and external links were still keyed off the NiceGUI native proxy.

Changes:

1. Exposed `PoolLauncher.main_window` for the existing Option C main pywebview window.
2. Refactored `_py_web_view.py` to resolve the dialog window from either the NiceGUI proxy (legacy single-window) or the Option C launcher main window. Real pywebview dialogs run through `run.io_bound`; the proxy path is unchanged.
3. Fixed `LoadSaveView._is_native_mode()` to detect Option C via `get_pool_launcher()` or the NiceGUI proxy, restoring browser upload behavior when neither is present.
4. Added `is_pywebview_desktop()` in `nicewidgets/utils/clipboard.py`, using `webview.windows` as the Option C signal without importing `cloudscope`.
5. Updated ECharts, Plotly, and tree clipboard paths to use that helper.
6. Updated header GitHub link handling so Option C opens URLs in the system browser.

Lazy imports of `get_pool_launcher` avoid circular imports through `desktop_launcher` → `home_page` → `load_save_view`.

## Tests added or modified

- Added `tests/cloudscope/test_py_web_view.py`
- Added `tests/nicewidgets/test_clipboard_desktop.py`
- Updated native-mode and header tests in `test_load_save_view.py`, `test_header_view.py`, and `test_tree_widget_smoke.py`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_py_web_view.py tests/cloudscope/test_load_save_view.py tests/cloudscope/test_header_view.py tests/nicewidgets/test_clipboard_desktop.py tests/nicewidgets/test_tree_widget_smoke.py::test_copy_table_data_uses_pyperclip_in_native_window -q
uv run pytest -q
```

## Test results

- Focused tests: 47 passed
- Full suite: 1183 passed, 2 skipped

## Concerns or follow-ups

- Manual macOS verification is still recommended for Load Folder/File and plot clipboard copy in Option C desktop mode.
- If `run.io_bound` + direct `create_file_dialog` fails on a platform, add a pywebview method-queue bridge only in `_py_web_view.py`.
- `_prompt_for_save_path` is fixed but remains unused by current callers.
