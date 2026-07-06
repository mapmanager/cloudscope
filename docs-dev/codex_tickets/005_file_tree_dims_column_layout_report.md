# Ticket 005 — File tree Dims column and column layout

## Files changed

- `src/acqstore/schema.py`
- `src/acqstore/acq_image/file_loaders/base_file_loader.py`
- `src/acqstore/acq_image/acq_image.py`
- `src/nicewidgets/tree_widget/config.py`
- `src/nicewidgets/tree_widget/tree_widget.py`
- `src/cloudscope/schema_adapters.py`
- `src/cloudscope/views/file_list_tree_view.py`
- `tests/acqstore/test_acq_image_tree_rows.py`
- `tests/acqstore/test_acq_image_list.py`
- `tests/acqstore/test_analysis_pool.py`
- `tests/acqstore/test_image_header_dims_display.py` (new)
- `tests/cloudscope/test_schema_adapters.py`
- `tests/nicewidgets/test_tree_widget_smoke.py`

## Summary of implementation

1. **Dims column** — Added `dims` field to `ACQ_FILE_LIST_SCHEMA` (header **Dims**). `AcqImage.get_schema_row()` populates it via `ImageHeader.format_dims_display()` (e.g. `C:2 Y:10000 X:1024`). Analysis child rows remain `None` via existing `setdefault` logic.

2. **Disable column reorder** — Added `suppress_movable_columns` to `TreeWidgetConfig` (default `False`); enabled in `AcqImageListTreeView`.

3. **Disable auto-fit** — `AcqImageListTreeView` sets `auto_size_columns=False` and `fit_columns_on_grid_resize=False`.

4. **Wider name column** — `schema_to_column_defs(..., tree_group_display_field="name")` applies `minWidth: 260` and `flex: 1` on `name`, fixed widths on other visible tree columns.

No disk persistence and no `getColumnState` / `applyColumnState`.

## Tests added or modified

- `tests/acqstore/test_image_header_dims_display.py`
- `tests/acqstore/test_acq_image_tree_rows.py` — fake header + dims assertion
- `tests/cloudscope/test_schema_adapters.py` — tree column widths
- `tests/nicewidgets/test_tree_widget_smoke.py` — `suppress_movable_columns`
- `tests/acqstore/test_acq_image_list.py`, `tests/acqstore/test_analysis_pool.py` — fake schema rows include `dims`

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_acq_image_tree_rows.py tests/acqstore/test_schema.py tests/cloudscope/test_schema_adapters.py tests/nicewidgets/test_tree_widget_smoke.py tests/cloudscope/test_file_list_tree_view.py -q
uv run pytest -q
```

## Test results

- Focused tree/schema tests: **68 passed**
- Full suite: **1229 passed**, 15 warnings

## Concerns or follow-ups

- If column widths still reset on `set_data` after disabling auto-fit, follow up by changing `TreeWidget._push_row_data_to_grid()` to update row data without a full `grid.update()` (no column-state persistence planned).
