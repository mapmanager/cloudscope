# 119_relocate_nicewidgets_raster_viewer_tests_report

## Files changed

- `tests/nicewidgets/test_raster_viewer_image_model.py` (new)
- `tests/nicewidgets/test_raster_viewer_pyramid.py` (new)
- `tests/nicewidgets/test_plotly_viewer_square_plot.py` (new)
- `tests/nicewidgets/test_raster_service.py` (merged 9 unique tests)
- `docs/developers/index.md` (policy note: tests never under `src/`)
- Deleted `src/nicewidgets/raster_viewer/tests/` (7 files)

## Summary

Relocated orphaned raster-viewer unit tests from `src/nicewidgets/raster_viewer/tests/` into the canonical `tests/nicewidgets/` tree. The misplaced suite was not collected by pytest (`testpaths = ["tests"]`). Ported ~27 unique tests; dropped ~23 redundant duplicates already covered by `test_raster_service.py` and `test_plotly_viewer_state.py`.

Four ported raster-service tests had stale pyramid-level expectations (assumed 4 levels on a 16×32 fixture that only builds 2 levels due to `MIN_PYRAMID_AXIS=6`). Updated test assertions to match current API behavior — no production code changes.

## Tests added or modified

- Added: `test_raster_viewer_image_model.py` (5 tests)
- Added: `test_raster_viewer_pyramid.py` (5 tests)
- Added: `test_plotly_viewer_square_plot.py` (11 tests)
- Modified: `test_raster_service.py` (+9 tests)

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_raster_viewer_image_model.py tests/nicewidgets/test_raster_viewer_pyramid.py tests/nicewidgets/test_plotly_viewer_square_plot.py tests/nicewidgets/test_raster_service.py -q
uv run pytest -q
```

## Test results

- Focused ported files: 56 passed
- Full suite: 1726 passed, 15 warnings

## Concerns or follow-ups

- None. No API bugs found; failures were incorrect test expectations from stale fixture assumptions.
