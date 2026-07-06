# 112 — Step 2: Load/Save in main header + file-list open/peek fixes

## Files changed

- `src/cloudscope/views/header_view.py` — `build_main_header()` accepts optional `load_save_view` and mounts it compactly after the title.
- `src/cloudscope/views/load_save_view.py` — Added `compact` build mode with dense/no-caps button props for header placement.
- `src/cloudscope/pages/home_page.py` — Load/Save built via header; removed from file-list splitter `.before`; open always restores splitter when transitioning from closed.
- `src/cloudscope/views/splitter_manager.py` — Peek raised from 2.5% → 6.0% (header-only `.before` pane).
- `tests/cloudscope/test_header_view.py` — Signature test for `load_save_view` parameter.

## Summary of implementation

**Load/Save → header:** Pre-built `LoadSaveView` is passed to `build_main_header(..., load_save_view=...)` and registered with `ViewManager` after the header builds. File-list `.before` now contains only the toggle header row and `AcqImageListTreeView`.

**Open from closed:** `_open_file_list_panel()` always calls `restore_open_value(FILE_LIST)` when `panel_open_state['file_list']` was false (replaces Option A collapsed-only restore).

**Peek tuning:** `HOME_FILE_LIST_PEEK_SPLITTER_PCT` increased to **6.0%** so the chevron row stays visible when closed without Load/Save consuming the peek pane.

## Tests added or modified

- `tests/cloudscope/test_header_view.py` — assert `load_save_view` in `build_main_header` signature.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_header_view.py tests/cloudscope/test_splitter_manager.py tests/cloudscope/test_load_save_view.py tests/cloudscope/test_home_page_build.py -q
```

## Test results

68 passed.

## Browser verification

| Check | Result |
|-------|--------|
| Load/Save in app header (`q-header`) | Pass |
| Load/Save not in file-list `.before` | Pass |
| Closed peek: header row visible (~31px before pane) | Pass |
| Open from closed: splitter expands (31→57px) | Pass |
| Close: returns to peek, header still visible | Pass |

## Concerns or follow-ups

- Header may feel tight on narrow windows with full Load/Save + upload control; further compact styling can wait for user feedback.
- Phase B (re-point `visible_file_ids_provider` to left-toolbar file list) still deferred.
