# Split experiment and image-header metadata views

## Files changed

- `src/cloudscope/views/view_ids.py`
- `src/cloudscope/views/left_toolbar_view.py`
- `src/cloudscope/views/metadata_widget/experiment_metadata_view.py` (new)
- `src/cloudscope/views/metadata_widget/image_header_metadata_view.py` (new)
- `src/cloudscope/views/metadata_widget/metadata_view.py` (deleted)
- `tests/cloudscope/test_experiment_metadata_view.py` (new)
- `tests/cloudscope/test_image_header_metadata_view.py` (new)
- `tests/cloudscope/test_metadata_view.py` (deleted)
- `tests/cloudscope/test_left_toolbar_view.py`
- `tests/cloudscope/test_view_manager.py`
- `tests/cloudscope/test_base_view.py`
- `tests/cloudscope/test_base_view_busy.py`

## Summary of implementation

- Replaced combined `MetadataView` / `ViewId.METADATA` with two independent
  left-toolbar views:
  - `ExperimentMetadataView` (`ViewId.EXPERIMENT_METADATA`) — per-field editor
  - `ImageHeaderMetadataView` (`ViewId.IMAGE_HEADER_METADATA`) — Apply card
- Left toolbar tabs: **Experimental Metadata** (`description`) and **Image
  Header** (`biotech`), before Velocity/Diameter/Config/App info.
- Each view owns its own selection sync and `MetadataChanged` handling filtered
  to its backend section id.
- Deleted `MetadataView` and `ViewId.METADATA` (no alias retained).

## Tests added or modified

- Added: `tests/cloudscope/test_experiment_metadata_view.py`
- Added: `tests/cloudscope/test_image_header_metadata_view.py`
- Deleted: `tests/cloudscope/test_metadata_view.py`
- Modified: left toolbar, view manager, base view tests

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_experiment_metadata_view.py \
  tests/cloudscope/test_image_header_metadata_view.py \
  tests/cloudscope/test_left_toolbar_view.py \
  tests/cloudscope/test_view_manager.py \
  tests/cloudscope/test_base_view.py \
  tests/cloudscope/test_base_view_busy.py \
  tests/cloudscope/test_experiment_metadata_editor_view.py \
  tests/cloudscope/test_schema_card_widget.py -q
```

## Test results

- **54 passed**

## Concerns or follow-ups

- Browser-verify both toolbar tabs independently after file selection.
- `schema_card_widget.py` remains shared with `AppConfigView`.
