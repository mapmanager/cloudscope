# 002 — Informative raster load error reporting

## Files changed

- `src/acqstore/acq_image/file_loaders/base_file_loader.py`
- `src/cloudscope/utils/load_errors.py`
- `src/cloudscope/views/primary_image_view.py`
- `src/cloudscope/views/reference_image_view.py`
- `tests/acqstore/test_base_file_loader_roi_and_physical.py`
- `tests/cloudscope/test_load_errors.py`
- `docs-dev/codex_tickets/002_load_error_reporting_report.md`

## Summary of implementation

Load failures when the header reports multiple channels but the loaded volume
has no ``C`` axis now raise a compact, contextual ``ValueError`` from
``BaseFileLoader`` (path, dims, loaded shape, channel index).

CloudScope raster views use new ``format_raster_load_error`` in
``cloudscope/utils/load_errors.py`` to split presentation:

- **``ui.notify``:** short toast, e.g.
  ``20220608_cell11.tif (ch 0): 2 channels in header, image has no C axis``
- **`logger.exception`:** full line including basename, channel, ``file_id``,
  and ``str(exc)``, plus traceback

Applied to primary and reference image load paths.

**Deferred:** ``AcqImageDataController`` status-bar messages; incomplete Olympus
sibling policy (Case 2).

## Tests added or modified

- `test_get_slice_data_loaded_missing_channel_axis_includes_context`
- `test_format_raster_load_error_short_notify_for_missing_channel_axis`
- `test_format_raster_load_error_truncates_long_unknown_errors`

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_base_file_loader_roi_and_physical.py tests/cloudscope/test_load_errors.py -q
uv run pytest tests/acqstore/ tests/cloudscope/test_load_errors.py -q
```

## Test results

- Focused tests: passed
- Full acqstore + load_errors: passed

## Concerns or follow-ups

- Align ``AcqImageDataController`` lazy-load status with ``load_errors`` helper.
- Fix or policy for incomplete Olympus split-channel TIFF pairs.
