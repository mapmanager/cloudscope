# 028 Home Splitter Minimize Reference Scroll Report

## Files changed

- `src/cloudscope/app_config.py`
- `src/cloudscope/pages/home_page.py`
- `src/cloudscope/views/splitter_manager.py`
- `tests/cloudscope/test_app_config_splitters.py`
- `tests/cloudscope/test_splitter_manager.py`

## Summary of implementation

- Allowed the Home page `FILE_LIST`, `PRIMARY_IMAGE`, and `ANALYSIS_REFERENCE` splitter `before` panes to collapse to `0.0%`.
- Kept the `LEFT_TOOLBAR` splitter lower bound unchanged so the closed icon rail remains available.
- Updated AppConfig normalization so persisted `0.0%` splitter values for the collapsible content splitters survive config load.
- Added an internal scroll container only around the reference-image pane so the bottom reference image can be scrolled when its pane is smaller than the fixed-height viewer content.

## Tests added or modified

- Added SplitterManager coverage for zero-percent collapse on the three content splitters.
- Added SplitterManager coverage confirming the left toolbar closed rail limit is unchanged.
- Added AppConfig coverage confirming persisted zero splitter values are restored on load.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_splitter_manager.py tests/cloudscope/test_app_config_splitters.py
uv run pytest
```

## Test results

- `uv run pytest tests/cloudscope/test_splitter_manager.py tests/cloudscope/test_app_config_splitters.py`: 12 passed.
- `uv run pytest`: 839 passed, 3 warnings.

Warnings observed in the full suite were pre-existing-style runtime/collection warnings:

- `PytestCollectionWarning` for `TestEvent` in `tests/cloudscope/test_base_view.py`.
- Two `RuntimeWarning: All-NaN slice encountered` warnings in `src/nicewidgets/raster_viewer/backend/raster_service.py`.

## Concerns or follow-ups

- The splitter upper bounds remain unchanged by design, so this ticket only fully minimizes `before` panes.
- The left toolbar lower bound remains unchanged by design because it represents the closed icon rail width.
- The reference image fix is scoped to the bottom reference-image pane; other fill-layout panes still use `overflow-hidden`.
