# 098 — NicePool X/Y column picker AG Grid empty display fix

## Files changed

- `src/nicewidgets/nicepool/pool_control_panel.py`
- `tests/nicewidgets/test_pool_control_panel_column_picker.py`

## Summary of implementation

Ticket 090 added a pinned `#` index column to the X/Y column picker AG Grids. In the
browser the grids showed scrollbars but no visible row/cell content.

Root cause (matches prior tree-widget index lessons in
`tree_widget_index_column_display_fix_report.md` and ticket 090 follow-up):

1. **`field: "index"` + `type: "numericColumn"`** — AG Grid's numeric column type can
   hijack display away from `rowData`, leaving cells blank while row count/scrollbars
   remain.
2. **`autoSizeStrategy: { type: "fitGridWidth" }`** with a pinned index column in a
   narrow half-width panel — risk of zero-width body columns in compact layouts.

Fix applied:

- Rename index field to **`column_index`** (non-reserved name; values still 1-based in
  `rowData`).
- **Remove `numericColumn`** — bind directly from `rowData` like `TableWidget` docs
  recommend for flat tables (tree widget explicitly removed this type for the same
  class of bug).
- **`sortable: False`** on index — display order matches dataframe column order only.
- **Remove `autoSizeStrategy`**; keep `flex: 1` + `minWidth: 120` on the name column.
- Add **`lockPosition: "left"`** and explicit **`domLayout: "normal"`**.

Selection identity unchanged: `getRowId` still keys on `column`.

## Tests added or modified

- `tests/nicewidgets/test_pool_control_panel_column_picker.py` — asserts `column_index`
  field, no `numericColumn`, no `autoSizeStrategy`, index not sortable.

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_pool_control_panel_column_picker.py -q
```

## Test results

```
1 passed in 0.78s
```

## Concerns or follow-ups

- Browser smoke on `/pool` with a loaded velocity-pool dataframe was attempted but
  Cursor browser MCP navigation stayed on `about:blank`; please confirm visually in
  your session.
- Remaining right-pool vertical band (~mostly gone) is a separate layout item from
  ticket 097.
