# File tree splitter height responsiveness

## Files changed

- `src/cloudscope/pages/home_page.py`
- `src/cloudscope/views/file_list_tree_view.py`
- `tests/cloudscope/test_file_list_tree_view.py`
- `docs-dev/codex_tickets/file_tree_splitter_height_report.md`

## Summary of implementation

The file-list pane on the Home page (`SplitterId.FILE_LIST`, `file_list_splitter.before`) now uses the same flex fill layout as the image panes (`_fill_column_classes()` instead of `_content_column_classes()`).

`AcqImageListTreeView.build()` creates a flex fill root column (`flex-1 min-h-0 overflow-hidden`) and passes it explicitly to `TreeWidget.build(parent=...)`. This avoids the nicewidgets default `height: 24rem` wrapper that applied when no sized parent was provided.

No column-width or AG Grid column-resize behavior was changed. Vertical height only.

## Follow-up (not in this ticket)

Consider a nicewidgets follow-up to change `TreeWidget.build()` default container from `height: 24rem` to `h-full` when no parent is passed, mirroring embedded use cases more closely.

## Tests added or modified

- Added `test_build_passes_sized_parent_to_tree_widget` in `tests/cloudscope/test_file_list_tree_view.py`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_file_list_tree_view.py -v
```

## Test results

17 passed in 1.49s (all tests in `tests/cloudscope/test_file_list_tree_view.py`).

## Concerns or follow-ups

- Manual browser verification: drag the file-list splitter and confirm the AG Grid body grows/shrinks with the pane while the load/save toolbar stays fixed.
- Legacy `AcqImageListTableView` has the same 24rem default path if re-enabled on Home; apply the same pattern there if needed.
