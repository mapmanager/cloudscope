# 090 — NicePool X/Y column picker index column

## Files changed

- `src/nicewidgets/nicepool/pool_control_panel.py`
- `tests/nicewidgets/test_pool_control_panel_column_picker.py`

## Summary of implementation

Added a pinned `#` index column to the X and Y column selector AG Grids in
`PoolControlPanel._create_column_aggrid`. Row data now includes 1-based `index`
values matching `df.columns` order. Selection identity remains on the `column`
field (`getRowId` unchanged).

Also set `suppressMovableColumns: True` so users cannot drag-reorder columns,
and sized the index column (`width`/`minWidth` 56px) so three-digit indices
(≥100) are not clipped under compact styling.

## Tests added or modified

- `tests/nicewidgets/test_pool_control_panel_column_picker.py` — verifies row
  data indices (including row 100), index column def, `suppressMovableColumns`,
  and unchanged `getRowId`.

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_pool_control_panel_column_picker.py -q
```

## Test results

```
1 passed in 0.80s
```

## Concerns or follow-ups

- Browser smoke on a live NicePool with 100+ columns is recommended but was not
  run in this pass (headless unit test covers grid options construction).
- Column grouping / AG Grid Enterprise remains deferred.
