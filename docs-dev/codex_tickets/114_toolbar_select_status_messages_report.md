# 114 — Revert toolbar singleton disable; informative load/save status

## Files changed

- `src/nicewidgets/image_toolbar_widget/image_toolbar_widget.py`
- `src/acqstore/acq_image/acq_image_list.py`
- `src/cloudscope/controllers/load_save_controller.py`
- `tests/nicewidgets/test_image_toolbar_widget_handlers.py`
- `tests/cloudscope/test_load_save_controller.py`

## Summary of implementation

1. **Image toolbar channel/ROI selects**
   - Reverted disable-when-singleton behavior: selects stay enabled with one option (prior UX).
   - Width `w-14` → `w-24` (~14% narrower than original `w-28`).

2. **Save selected status**
   - Completion message now includes the saved file name, e.g. `Saved a.tif` (footer + `ui.notify` via `AppStatusChanged`).

3. **Load folder/file completion status**
   - Added `LoadResult.discovered_count` (total candidates discovered before load attempts).
   - Completion message format: `Load completed (m/n)`; warnings append ` with k warning(s)`.
   - Fallback when `discovered_count` is unset but files loaded: `n = m` for backward-compatible mocks.

## Tests added or modified

- `test_image_toolbar_widget_handlers.py`: singleton tests now assert selects remain **enabled**.
- `test_load_save_controller.py`: save completion expects `Saved a.tif`; load path test expects `Load completed (1/2) with 1 warning(s)`.

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_image_toolbar_widget_handlers.py tests/cloudscope/test_load_save_controller.py -q
uv run pytest tests/acqstore/test_acq_image_list_progress_cancel.py tests/acqstore/test_acq_image_list.py -q
```

## Test results

- Toolbar + load/save controller: **67 passed**
- Acqstore load tests: **all passed**

## Concerns or follow-ups

- None.
