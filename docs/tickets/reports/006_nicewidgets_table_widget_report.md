# Ticket report: 006 NiceGUI `TableWidget` (`nicewidgets`)

## Files changed

- `src/nicewidgets/__init__.py` (new)
- `src/nicewidgets/table_widget/__init__.py` (new)
- `src/nicewidgets/table_widget/column_def.py` (new)
- `src/nicewidgets/table_widget/config.py` (new)
- `src/nicewidgets/table_widget/js_hooks.py` (new)
- `src/nicewidgets/table_widget/table_widget.py` (new, then refactored)
- `src/nicewidgets/table_widget/demo_app.py` (new, then updated)
- `src/nicewidgets/table_widget/README.md` (new, then updated)
- `tests/nicewidgets/test_table_widget_smoke.py` (new, expanded)

## Summary of implementation

- Added standalone package **`nicewidgets`** under `src/nicewidgets/` with **`table_widget`** submodule and **no re-exports** from `__init__.py` files.
- Added **`TableWidgetConfig`** (`config.py`) for grid-level behavior: selection mode, edit toggles, keyboard row-nav, selection clear-on-refresh, and option passthrough.
- Added **JS hook builders** (`js_hooks.py`) for AG Grid callbacks: row click emit, ArrowUp/ArrowDown row selection, start editing on double-click, and edit-stopped changed-value emit.
- Refactored **`TableWidget`**:
  - id-based row validation + `:getRowId` wiring,
  - modular APIs for `set_data`, `upsert_row`, `update_row`, `remove_row`,
  - programmatic selection: `set_selected_row_ids`, `get_selected_row_ids`, `get_selected_rows`, `clear_selection`,
  - edit callback: `on_cell_edited(row_id, field, old, new, row_dict)`,
  - context menu extensibility: built-in column toggles plus optional `on_build_context_menu(table_widget)`.
- Updated **`demo_app.py`** to demonstrate programmatic selection buttons, edit callback, and custom context menu items.

## Tests added or modified

- `tests/nicewidgets/test_table_widget_smoke.py` — expanded to cover:
  - config defaults,
  - JS hook string builders,
  - programmatic selection API behavior,
  - `set_data` selection clearing semantics,
  - row update path,
  - emitted selection/edit event handlers and callback wiring.

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_table_widget_smoke.py -v
uv run pytest
```

## Test results

- `tests/nicewidgets/test_table_widget_smoke.py`: **18 passed**
- Full suite: **90 passed**

## Concerns or follow-ups

- **Live UI**: Context menu + AG Grid behavior was not exercised by automated browser tests; run **`uv run python -m nicewidgets.table_widget.demo_app`** and verify right-click on the grid wrapper and row clicks locally.
- **`grid_options` overrides**: Conflicting **`getRowId`** / **`rowSelection`** can break assumptions; README documents caution.
- **Packaging**: `pyproject.toml` was not changed; if wheels must expose `nicewidgets` explicitly for distribution, confirm **`uv_build`** package discovery for this layout.
