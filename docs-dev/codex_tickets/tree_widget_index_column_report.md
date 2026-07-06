# Tree widget optional Index column (top-level load order)

## Files changed

- `src/nicewidgets/tree_widget/config.py`
- `src/nicewidgets/tree_widget/tree_widget.py`
- `src/nicewidgets/tree_widget/README.md`
- `src/cloudscope/views/file_list_tree_view.py`
- `tests/nicewidgets/test_tree_widget_smoke.py`

## Summary of implementation

Added optional synthetic **Index** column to `TreeWidget`, mirroring `TableWidget` but with tree-specific semantics:

- Config: `show_index_column` (default `False`), `index_field` (`tree_row_index`), `index_header` (`Index`)
- When enabled, prepends a narrow numeric column and assigns 1-based indices in **`rowData` load order** to **top-level rows only** (`len(path_field) == 1`)
- Child/analysis rows receive `None` (blank cell)
- Indices refresh on `set_data`, `update_row`, and `replace_group_rows`
- Enabled in `AcqImageListTreeView` via `TreeWidgetConfig(show_index_column=True)`

No AcqStore or schema changes; index is synthetic widget data only.

## Tests added or modified

- Modified: `tests/nicewidgets/test_tree_widget_smoke.py` (config defaults, index assignment, set_data, replace_group_rows, opt-out, field conflict)

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_tree_widget_smoke.py tests/cloudscope/test_file_list_tree_view.py -q
```

## Test results

45 passed in 1.55s

## Concerns or follow-ups

- Index follows load order (Option A), not visible order after filter/sort; batch analysis visible order remains `get_displayed_file_ids()`.
