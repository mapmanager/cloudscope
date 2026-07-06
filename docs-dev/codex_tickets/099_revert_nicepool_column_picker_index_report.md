# 099 — Revert NicePool X/Y column picker index column

## Files changed

- `src/nicewidgets/nicepool/pool_control_panel.py` — restored `_create_column_aggrid` to pre-06e8d85
- `tests/nicewidgets/test_pool_control_panel_column_picker.py` — deleted (added with index column)

## Summary

Reverted all index-column work on X/Y AG Grids. Source of truth: parent of commit
`06e8d85` (`git show 06e8d85^:.../pool_control_panel.py`).

## Tests

```bash
uv run pytest tests/nicewidgets/test_nicepool.py tests/nicewidgets/test_plot_pool_controller.py -q
```
