# 111 — Home file list custom header (replace SmartExpansion)

## Files changed

- `src/cloudscope/pages/home_page.py` — Replaced `SmartExpansion` wrapper with clickable header row + direct `AcqImageListTreeView` mount; Option A open semantics (restore splitter only when collapsed); updated reset-layout path.
- `src/cloudscope/views/splitter_manager.py` — Added `is_file_list_collapsed()`; updated peek docstrings (no SmartExpansion reference).
- `tests/cloudscope/test_splitter_manager.py` — Added `test_splitter_manager_is_file_list_collapsed`.

## Summary of implementation

Removed `ui.expansion` / `SmartExpansion` from the home file-list path. Layout in `file_list_splitter.before` is now:

```
column (fill)
  load_save_view
  column (flex-1)
    header row (icon + "File list" + chevron) — always visible, click toggles
    column (flex-1) → AcqImageListTreeView (direct flex child, no q-expansion)
```

**Open:** `panel_open_state['file_list'] = True`; if `splitter_manager.is_file_list_collapsed()` then `restore_open_value(FILE_LIST)`; else leave splitter unchanged (Option A); `file_list_panel.show()`; sync chevron.

**Close:** hide tree, `collapse_file_list_to_peek()`, sync chevron.

**Default:** closed (peek + hidden tree), same as Step 1 intent.

**Reset layout:** `_reset_home_expansions()` calls `_open_file_list_panel()` instead of `SmartExpansion.open()` for file list.

## Tests added or modified

- Added `test_splitter_manager_is_file_list_collapsed` in `tests/cloudscope/test_splitter_manager.py`.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_splitter_manager.py tests/cloudscope/test_smart_expansion_integration.py tests/cloudscope/test_home_page_build.py -q
```

## Test results

24 passed.

## Browser verification (acceptance)

Server: `CLOUDSCOPE_NATIVE=0 CLOUDSCOPE_PORT=8766 CLOUDSCOPE_SHOW=0 uv run python src/cloudscope/app.py`

| Check | Result |
|-------|--------|
| No `q-expansion-item` in file-list `.before` pane | Pass (`qExpansionInFileListBefore: false`) |
| Custom header present | Pass |
| Cold start closed: peek ~13–24px, grid hidden | Pass |
| Open from peek: splitter expands (13→57px at 459px viewport; 24→106px at 900px viewport) | Pass |
| Close: returns to peek, grid hidden | Pass |
| Chevron rotates with open/close | Pass |
| Tree is direct flex descendant (no expansion content slot) | Pass |

**Grid height note:** At default 18% open splitter share, Load/Save (~42px) + header (~27px) consume most of the `.before` pane, so AG Grid `clientHeight` is small (≈16px at 459px viewport) until the user drags the horizontal handle taller or Step 2 moves Load/Save to the main header. This is expected; the prior bug was grid stuck at ~2px inside `q-expansion-item__content` regardless of pane height. With the custom header, grid height tracks remaining flex space in the tree column.

Could not automate splitter drag in browser MCP (Vue modelValue not settable from CDP); Option A “no splitter move when already expanded” is covered by unit logic on `is_file_list_collapsed()`.

## Concerns or follow-ups

- **Step 2 (separate ticket):** Move `LoadSaveView` into `build_main_header` so peek/open panes are header-only and the tree gets usable height at default open %.
- Header row uses `ui.row` + click handler (not `ui.button`); a11y could be improved later with an explicit button if needed.
- Phase B (re-point `visible_file_ids_provider` to left-toolbar file list) remains deferred.
