# 058 — Reference image metadata card on Image Header tab

## Files changed

- `src/cloudscope/views/metadata_widget/image_header_metadata_view.py`
- `tests/cloudscope/test_image_header_metadata_view.py`
- `docs-dev/cursor_tickets/058_reference_image_metadata_gui_report.md`

## Summary of implementation

On the left-toolbar **Image Header** tab, added a second read-only
`SchemaCardWidget` titled **Reference Image** below the existing **Image
Header** card (unchanged, including editable calibration + Apply).

Behavior:

- File with reference: show card populated from
  `acq_image.get_metadata_section('reference_image_metadata')`.
- File without reference: show *"No reference image for this file"* (card hidden).
- No file / demo selection: hide both reference message and card (same as header).

Uses `REFERENCE_IMAGE_METADATA_SCHEMA` from acqstore. No new tab, no edit/apply
wiring, no controller changes.

## Tests added or modified

- `test_sync_selection_shows_no_reference_message_when_file_lacks_reference`
- `test_sync_selection_populates_reference_card_when_present`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_image_header_metadata_view.py tests/cloudscope/test_left_toolbar_view.py -q
```

## Test results

- **15 passed** (9 image header + 6 left toolbar)

## Concerns or follow-ups

- Selecting a file with reference while the Image Header tab is visible decodes
  reference metadata (acceptable per ticket scope).
- Browser verification on real OIR with reference optional.
