# Ticket Report: 002 AcqImageList Protocol and Schema

## Files Changed

- `src/acqstore/acq_image/acq_image.py`
- `src/acqstore/acq_image/acq_image_list.py`
- `src/acqstore/schema.py`
- `src/cloudscope/core/contracts/acq_file_list.py`
- `tests/acqstore/test_acq_image_list.py`
- `tests/acqstore/test_schema.py`
- `docs/acqstore/schemas.md`
- `docs/tickets/reports/002_acq_image_list_protocol_and_schema_report.md`

## Summary of Implementation

- Expanded `AcqImageList` into a protocol-shaped ordered collection with stable path ordering, file lookup helpers, default selection helpers, dirty/save helpers, and table schema projection.
- Added generator-style `iter_save_all()` progress events with optional cancellation callback and kept `save_all()` as a convenience wrapper.
- Added `AcqImage` default selection helpers (`get_default_channel`, `get_default_roi`) and concrete dirty/save behavior tied to ROI dirty state.
- Introduced backend-owned schema module (`SchemaDefinition`, `FieldSchema`, view hints, semantic kind enum) with v1 `acq_file_list` schema.
- Updated CloudScope list contract tuple ROI type from `str | None` to `int | None` and added `iter_save_all(...)` signature.
- Added schema documentation under `docs/acqstore/schemas.md`.

## Tests Added or Modified

- Added `tests/acqstore/test_acq_image_list.py`
- Added `tests/acqstore/test_schema.py`
- Updated `tests/acqstore/test_roi.py` (property access alignment for `num_rois`)

## Exact Test Commands Run

- `uv run pytest`

## Test Results

- `54 passed` using `uv run pytest`.

## Concerns or Follow-ups

- CloudScope app-level events/state still type ROI IDs as strings in several files; this report only updates the file-list contract. A follow-up pass should align controller/events/state contracts to `int | None`.
