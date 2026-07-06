# Experiment metadata editor refactor

## Files changed

- `src/acqstore/acq_image/acq_image_list.py`
- `src/cloudscope/views/metadata_widget/preset_select.py` (new)
- `src/cloudscope/views/metadata_widget/experiment_metadata_editor_view.py` (new)
- `src/cloudscope/views/metadata_widget/metadata_view.py`
- `tests/acqstore/test_acq_image_list_unique_metadata.py` (new)
- `tests/cloudscope/test_experiment_metadata_editor_view.py` (new)
- `tests/cloudscope/test_metadata_view.py`

## Summary of implementation

- Added `AcqImageList.get_unique_metadata_values(field_name)` for sorted unique
  non-empty string values across loaded files (`experiment_metadata` STR fields
  only).
- Added `preset_select.make_preset_str_select` using NiceGUI 3.10.0
  `ui.select(..., new_value_mode='add')` with lazy preset loading and
  commit-on-blur/Enter/preset semantics.
- Added `ExperimentMetadataEditorView` with per-field commit (no Apply button).
  String fields use combobox presets except `note`, which remains `ui.input`.
  Numeric fields use `ui.number`.
- Refactored `MetadataView` to orchestrate the new experiment editor plus an
  unchanged `SchemaCardWidget` Apply card for image header metadata only.
  Selection sync no longer clears/rebuilds the entire container on file change.

## MVC impact

- **Unchanged:** `ApplyMetadataIntent`, `MetadataChanged`,
  `HomePageController._on_apply_metadata`, file tree / velocity pool subscribers.
- Experiment commits publish single-field `ApplyMetadataIntent` patches.

## Tests added or modified

- Added: `tests/acqstore/test_acq_image_list_unique_metadata.py`
- Added: `tests/cloudscope/test_experiment_metadata_editor_view.py`
- Modified: `tests/cloudscope/test_metadata_view.py`

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_acq_image_list_unique_metadata.py tests/cloudscope/test_experiment_metadata_editor_view.py tests/cloudscope/test_metadata_view.py tests/cloudscope/test_apply_metadata.py -q

uv run pytest tests/cloudscope/test_left_toolbar_view.py tests/cloudscope/test_schema_card_widget.py tests/cloudscope/test_file_list_tree_view.py -q
```

## Test results

- **20 passed** (focused metadata suite)
- **32 passed** (related view suite)

## Concerns or follow-ups

- **Follow-up ticket:** Split experiment and image-header metadata into two
  separate left-toolbar views (each with its own schema-driven editor).
- Browser-verify combobox preset pick, free-form entry, and programmatic sync on
  NiceGUI 3.10.0 (NiceGUI docstring notes `new_value_mode` may be ineffective
  for purely programmatic value sets).
- Image header editing remains on legacy Apply card; no acqstore header changes.
- **Fix (post-implementation):** `SchemaCardWidget.update_values()` now refreshes
  read-only value labels so header metadata displays correctly when the card is
  built once and synced on file selection.
