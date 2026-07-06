# Tree widget index column display fix

## Files changed

- `src/nicewidgets/tree_widget/config.py`
- `src/nicewidgets/tree_widget/tree_widget.py`
- `src/nicewidgets/tree_widget/README.md`
- `tests/nicewidgets/test_tree_widget_smoke.py`

## Summary of implementation

Fixed AG Grid tree Index column showing wrong values (e.g. file count `341` on the first row until hide/show) and sort-related reorder bugs.

- **Blank header:** default `index_header=''` (column stays visible)
- **Non-sortable:** `sortable: False` — index is load-order display only
- **Explicit binding:** `:valueGetter` reads `row.data[index_field]`; child rows render `''`
- **Removed `numericColumn` type** — avoided AG Grid internal row-index display path
- **Narrow width:** `index_column_width_px(cell_font_size_px, digits=4)` replaces fixed `maxWidth: 96`
- **`lockPosition: 'left'`** on index column
- Context menu uses field name when header is blank

Python `_assign_row_indices()` unchanged (still 1-based for top-level rows).

User confirmed ~341 matched file-row count, supporting a display bug rather than bad assignment.

## Follow-up (not in this ticket)

Apply font-scaled column width helpers to other tree columns (schema-driven widths in CloudScope).

## Tests added or modified

- Modified: `tests/nicewidgets/test_tree_widget_smoke.py`

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_tree_widget_smoke.py tests/cloudscope/test_file_list_tree_view.py -q
```

## Test results

46 passed in 1.77s

## Concerns or follow-ups

- Manual verify: first file row shows `1` on initial load without hide/show; sort header on index column should not be clickable.
