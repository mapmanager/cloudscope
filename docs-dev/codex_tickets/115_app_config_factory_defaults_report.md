# 115 — App config factory defaults button

## Files changed

- `src/cloudscope/app_config.py`
- `src/cloudscope/views/app_config_view.py`
- `tests/cloudscope/test_app_config.py`
- `tests/cloudscope/test_app_config_view.py`
- `docs-dev/codex_tickets/115_app_config_factory_defaults_report.md`

## Summary of implementation

- Added `APP_CONFIG_EDITABLE_SETTINGS_FIELDS` and
  `AppConfig.reset_editable_settings_to_factory_defaults()` to restore the five
  Config-panel fields from a fresh `AppConfigData()` while preserving recents,
  last path, window geometry, splitters, dark mode, and channel LUT defaults.
- Reset persists immediately via `normalize_and_persist()`.
- Updated `AppConfigView` to use a two-column editable layout
  (`SchemaCardWidget(editable_columns=2)`) matching other metadata panels.
- Added **Factory defaults** button on the same row as **Reset View** (after it).

## Tests added or modified

- `test_reset_editable_settings_to_factory_defaults` in `test_app_config.py`
- `test_app_config_ui_schema_editable_subset` now asserts alignment with
  `APP_CONFIG_EDITABLE_SETTINGS_FIELDS`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_app_config.py tests/cloudscope/test_app_config_view.py
```

## Test results

16 passed (`tests/cloudscope/test_app_config.py`, `tests/cloudscope/test_app_config_view.py`).

## Concerns or follow-ups

- Reset does not re-seed contrast on already-loaded images (intentional, KISS).
- `text_size` full GUI re-application still requires page reload (unchanged).
