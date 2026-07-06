# 034 Move Events Into Velocity And Toolbar Cosmetics Report

## Files changed

- `src/cloudscope/views/load_save_view.py`
- `src/cloudscope/views/image_toolbar_view.py`
- `src/cloudscope/views/velocity_analysis_view.py`
- `src/cloudscope/views/left_toolbar_view.py`
- `tests/cloudscope/test_left_toolbar_view.py`
- `tests/cloudscope/test_velocity_analysis_view.py`
- `docs/codex_tickets/034_move_events_into_velocity_and_toolbar_cosmetics_report.md`

## Summary of implementation

- Moved `Load CSV` and `Load Sample Data` from standalone load/save toolbar buttons into the history menu, reusing the existing click handlers.
- Kept the history menu button enabled even when there are no recents so the new menu actions remain available.
- Right-aligned `Save Selected` and `Save All` in the load/save toolbar by adding margin auto to `Save Selected`.
- Right-aligned `ContrastWidget` in the image toolbar row by wrapping it in a right-pushed layout container.
- Removed the standalone `Events` tab from the left toolbar.
- Embedded `EventAnalysisView` inside `VelocityAnalysisView`, below the results/run/batch controls.
- Passed `AppConfig` into `VelocityAnalysisView` so embedded event table font sizing continues to use the configured table font size.
- Forwarded `VelocityAnalysisView` visibility to the embedded event view so event subscriptions are active only while the Velocity tab is open.
- Removed bottom pinning from the velocity controls so content flows top-to-bottom with the event editor below the batch button.

## Tests added or modified

- Updated `tests/cloudscope/test_left_toolbar_view.py` for the removed standalone `Events` tab.
- Added `tests/cloudscope/test_velocity_analysis_view.py` coverage for embedded `EventAnalysisView` ownership and visibility forwarding.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_load_save_view.py tests/cloudscope/test_left_toolbar_view.py tests/cloudscope/test_velocity_analysis_view.py tests/cloudscope/test_event_analysis_view.py tests/cloudscope/test_event_analysis_view_table_config.py
```

## Test results

- `69 passed in 1.04s`
- Rerun after lint cleanup: `69 passed in 1.00s`
- `ReadLints` found no linter errors in edited source/test files.

## Concerns or follow-ups

- None.
