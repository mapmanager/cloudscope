# Image toolbar compact select height and text-xs defaults

## Files changed

- `src/nicewidgets/compact_select_styles.py` (new)
- `src/nicewidgets/image_toolbar_widget/image_toolbar_widget.py`
- `src/nicewidgets/contrast_widget/contrast_widget.py`
- `src/cloudscope/app_config.py`
- `src/cloudscope/views/app_config_view.py`
- `src/nicewidgets/gui_defaults.py`
- `src/cloudscope/devtools/mvc_diagnostics_view.py`
- `tests/nicewidgets/test_compact_select_styles.py` (new)
- `tests/cloudscope/test_app_config.py`

## Summary of implementation

### Toolbar-only shorter `ui.select` (not app-wide)

Added `nicewidgets.compact_select_styles` with:

- Quasar props `standout dense hide-bottom-space options-dense` on Channel, ROI, and Color LUT selects only
- CSS class `nw-select-compact` (~30px field height) injected once via `ensure_compact_select_styles()`
- No changes to `setUpGuiDefaults` select defaults or other app selects

### `text-xs` factory default (no migration)

- `DEFAULT_TEXT_SIZE = 'text-xs'` in `AppConfig`
- App settings schema default updated to `text-xs`
- `setUpGuiDefaults` fallback parameter default is `text-xs`
- Existing saved `text_size` values in `app_config.json` are preserved on load
- `/dev/mvc` diagnostics page calls `setUpGuiDefaults('text-xs')` before building UI

Home and pool pages continue to call `setUpGuiDefaults(runtime.app_config.get_attribute('text_size'))` at page entry.

## Tests added or modified

- New: `tests/nicewidgets/test_compact_select_styles.py`
- Modified: `tests/cloudscope/test_app_config.py` (default + no-migration tests)

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_compact_select_styles.py tests/nicewidgets/test_image_toolbar_widget.py tests/nicewidgets/test_image_toolbar_widget_handlers.py tests/nicewidgets/test_contrast_widget.py tests/cloudscope/test_image_toolbar_view.py tests/cloudscope/test_app_config.py -q
```

## Test results

83 passed in 1.90s

## Concerns or follow-ups

- Manual visual check: compact selects in light and dark mode; open dropdown readability with `options-dense`
- Persisted `text-sm` users must switch to `text-xs` once in app settings if desired
