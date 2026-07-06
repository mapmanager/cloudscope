# Home file list SmartExpansion (Step 1)

## Files changed

- `src/cloudscope/views/splitter_manager.py` — peek collapse constant and `collapse_file_list_to_peek()`
- `src/cloudscope/pages/home_page.py` — SmartExpansion wiring, default closed, flex fill layout
- `tests/cloudscope/test_splitter_manager.py` — peek collapse tests

## Summary

Wrapped the home-page `AcqImageListTreeView` in `SmartExpansion` with lifecycle
callbacks tied to the existing `_open_file_list_panel` /
`_close_file_list_panel` helpers. The panel starts **closed**; closing collapses
`SplitterId.FILE_LIST` to **2.5%** (peek header) instead of 0%. Opening restores
the remembered open splitter value and shows the tree. A flex column wrapper lets
the tree fill the `.before` pane height when the user drags the file-list
splitter.

Load/save remains above the expansion in `.before` (unchanged this ticket).

`app_state.visible_file_ids_provider` remains wired to the **home** file list
(not the left-toolbar file list). Batch/pool file selection follows the home
tree grid when it is open and visible.

## Tests added or modified

- `tests/cloudscope/test_splitter_manager.py`

## Test commands run

```bash
uv run pytest tests/cloudscope/test_splitter_manager.py tests/cloudscope/test_smart_expansion_integration.py
```

## Test results

21 passed (`tests/cloudscope/test_splitter_manager.py`, `tests/cloudscope/test_smart_expansion_integration.py`).

## Concerns or follow-ups

- **Step 2:** Move `LoadSaveView` into `build_main_header` with compact styling.
- **Phase B:** Optionally re-point `visible_file_ids_provider` to the left-toolbar
  file list if home list stays closed by default during normal use.
- Reset layout still opens the home file-list expansion (intentional restore of
  full workspace layout).
