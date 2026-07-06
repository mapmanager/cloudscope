# App config: table font default 11 and remove dark mode from options panel

## Files changed

- `src/cloudscope/app_config.py`
- `src/cloudscope/views/app_config_view.py`
- `tests/cloudscope/test_app_config_view.py`

## Summary of implementation

- Changed `DEFAULT_TABLE_FONT_SIZE_PX` from `13` to `11`. Fresh installs and the options panel schema default now use 11px; existing saved values in `app_config.json` are unchanged on load.
- Removed the `dark_mode` field from `APP_CONFIG_UI_SCHEMA` so the left-toolbar Options panel no longer shows a dark-mode checkbox. Runtime dark mode (`AppConfigData.dark_mode`, header toggle, `ThemeChanged`, etc.) is unchanged.

## Tests added or modified

- Modified: `tests/cloudscope/test_app_config_view.py` (editable fields no longer include `dark_mode`)

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_app_config_view.py tests/cloudscope/test_app_config.py -q
```

## Test results

15 passed in 1.53s

## Concerns or follow-ups

- None. Dark mode remains configurable via the header toggle and persisted in `AppConfig`; only the Options panel control was removed.
