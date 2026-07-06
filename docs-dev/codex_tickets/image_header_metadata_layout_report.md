# Image header metadata layout and hide scenes

## Files changed

- `src/acqstore/acq_image/metadata.py`
- `src/cloudscope/views/metadata_widget/schema_card_widget.py`
- `src/cloudscope/views/metadata_widget/image_header_metadata_view.py`
- `tests/acqstore/test_metadata.py`
- `tests/cloudscope/test_schema_card_widget.py`

## Summary of implementation

- Set `visible=False` on `num_scenes` in `IMAGE_HEADER_METADATA_SCHEMA` so schema-driven
  UIs omit Scenes while backend `get_values()` still includes it.
- Added optional `readonly_columns` to `SchemaCardWidget` (default `1`). When `> 1`,
  read-only fields render in a NiceGUI grid; editable fields stay full width.
- Added optional `editable_columns` (default `1`) with the same grid behavior for
  editable controls.
- `ImageHeaderMetadataView` passes `readonly_columns=2` and `editable_columns=2`.

## Tests added or modified

- Added: `test_image_header_metadata_schema_hides_num_scenes_in_ui`
- Added: `test_readonly_columns_must_be_at_least_one`
- Added: `test_editable_columns_must_be_at_least_one`
- Added: `test_image_header_schema_excludes_num_scenes_from_visible_fields`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_schema_card_widget.py tests/acqstore/test_metadata.py tests/cloudscope/test_image_header_metadata_view.py -q
```

## Test results

- **43 passed** (schema card + header view; full metadata suite unchanged)

## Concerns or follow-ups

- Browser-verify Image Header tab: two-column read-only layout, no Scenes row,
  Calibration fields still full width with Apply.
