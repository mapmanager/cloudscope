# 063 AcqStore Server Reference Line ROI Log

## Files changed

- `src/acqstore_server/open_service.py`
- `tests/acqstore_server/test_open_service.py`
- `docs-dev/cursor_tickets/063_acqstore_server_reference_line_roi_log_report.md`

## Summary of implementation

- Added an INFO log line containing the reference image `lineRoi` values when
  a loaded file has a reference line segment.
- Files without a reference image or without `lineRoi` do not emit the line.

## Tests added or modified

- Updated the existing reference-image open test to capture the service log
  and assert the exact `lineRoi` message.

## Exact test commands run

```bash
uv run pytest tests/acqstore_server/test_open_service.py
```

## Test results

- 9 passed in 1.01s.

## Concerns or follow-ups

- None.
