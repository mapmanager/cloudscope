# Right pool main workspace minimum splitter width

## Files changed

- `src/cloudscope/app_config.py`
- `src/cloudscope/views/splitter_manager.py`
- `tests/cloudscope/test_splitter_manager.py`
- `tests/cloudscope/test_app_config_splitters.py`

## Summary of implementation

- Added `HOME_RIGHT_POOL_MAIN_MIN_SPLITTER_PCT = 25.0` as the single source of truth for the minimum width of the central main workspace when the right velocity-pool panel is open.
- Replaced the hardcoded `50.0` lower limit in `HOME_SPLITTER_PRESETS[SplitterId.RIGHT_POOL]` and in `AppConfig._normalize_loaded_data()` clamping for `home_right_pool_open_splitter_pct`.
- Default open layout (`DEFAULT_HOME_RIGHT_POOL_OPEN_SPLITTER_PCT = 72.0`) and collapsed pool behavior (`HOME_RIGHT_POOL_CLOSED_SPLITTER_PCT = 98.0`) are unchanged.

## Tests added or modified

- Added: `test_splitter_manager_right_pool_main_min_limit`
- Added: `test_splitter_manager_right_pool_set_value_clamps_to_main_min`
- Added: `test_app_config_right_pool_open_splitter_clamps_to_main_min_on_load`
- Added: `test_app_config_right_pool_open_splitter_keeps_at_main_min_on_load`
- Modified: `tests/cloudscope/test_splitter_manager.py` (imports)
- Modified: `tests/cloudscope/test_app_config_splitters.py` (imports)

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_splitter_manager.py tests/cloudscope/test_app_config_splitters.py
```

## Test results

- Focused: 20 passed

## Concerns or follow-ups

- Left-toolbar maximum (70%) still limits how narrow the combined middle column can become when the left panel is expanded; deferred to a separate change.
- Child content inside the main workspace (image toolbar, file tree columns) may overflow visually at 25% width; add `min-w-0` to central column classes only if manual testing shows issues.
