# 010 Save Selected dirty refresh report

## Files changed

- `src/cloudscope/views/load_save_view.py`
- `tests/cloudscope/test_load_save_view.py`

## Summary of implementation

- Root cause: `LoadSaveView` refreshed Save Selected on selection / analysis / event-analysis changes, but not on metadata apply. The file list already listened to `MetadataChanged`, so Genotype edits updated the tree while Save Selected stayed disabled.
- Subscribed `LoadSaveView` to `MetadataChanged` and `RoiChanged`, each calling `_update_button_states()`.
- Intentionally did **not** subscribe to `ImageContrastChanged`. Contrast load/save/display behavior is unchanged; contrast dirty/Save Selected coupling is deferred.

## Tests added or modified

- `test_metadata_changed_refreshes_save_selected_without_selection_change`
- `test_roi_changed_refreshes_save_selected_without_selection_change`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_load_save_view.py -q
```

## Test results

- `uv run pytest tests/cloudscope/test_load_save_view.py -q`: `42 passed in 1.54s`.

## Concerns or follow-ups

- Contrast sidecar is loaded into `AcqImage` but default primary-image display still prefers auto-per-slice; deciding whether contrast should dirty Save Selected remains a separate architecture ticket.
- Unloaded-row right-click context-menu UX remains a separate bug.
