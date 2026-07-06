# Left toolbar file list panel (Phase A)

## Files changed

- `src/cloudscope/views/view_ids.py` — add `ViewId.LEFT_TOOLBAR_FILE_LIST`
- `src/cloudscope/views/file_list_tree_view.py` — optional `default_visible_columns`, `_build_schema_column_defs`
- `src/cloudscope/views/left_panel_file_list_view.py` — compact column profile and widths
- `src/nicewidgets/tree_widget/config.py` — `index_column_width_multiplier`
- `src/nicewidgets/tree_widget/tree_widget.py` — apply index width multiplier
- `tests/cloudscope/test_left_panel_file_list_view.py` — toolbar column layout tests
- `tests/nicewidgets/test_tree_widget_smoke.py` — index width multiplier test
- `src/cloudscope/views/left_toolbar_view.py` — File List tab, construct, build, register
- `tests/cloudscope/test_left_toolbar_view.py` — panel composition assertions
- `tests/cloudscope/test_file_list_tree_view.py` — column profile and view id tests

## Summary

Phase A adds a **File List** panel to the left toolbar by reusing
`AcqImageListTreeView` through `LeftPanelFileListView`. The toolbar instance
uses a compact default column set (`name`, `loaded`, `saved`, `dims`) with
index column enabled at half default width; `loaded` and `saved` use minimal
marker column widths and blank headers. Other schema columns remain available
via the tree context-menu column toggles. The existing home-page file list
tree is unchanged.

## Tests added or modified

- `tests/cloudscope/test_left_toolbar_view.py`
- `tests/cloudscope/test_file_list_tree_view.py`

## Test commands run

```bash
uv run pytest tests/cloudscope/test_left_toolbar_view.py tests/cloudscope/test_file_list_tree_view.py
```

## Test results

23 passed (`tests/cloudscope/test_left_toolbar_view.py`, `tests/cloudscope/test_file_list_tree_view.py`).

## Concerns or follow-ups (Phase B and later)

- **Re-point `visible_file_ids_provider`** on `home_page.py` from the home file
  list to `left_toolbar.file_list_view.get_displayed_file_ids` so batch
  analysis respects the toolbar grid when the home list is collapsed or removed.
- Collapse or remove the home `SplitterId.FILE_LIST` pane to reclaim vertical
  space for primary image and analysis plots.
- Consider tighter `name` column min-width in `schema_adapters.py` for the narrow
  toolbar panel.
- Consider moving Load/Save controls to the main page header.
