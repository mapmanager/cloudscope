# Disable server load buttons report

## Files changed

- `src/cloudscope/views/load_save_view.py`
- `tests/cloudscope/test_load_save_view.py`
- `docs-dev/codex_tickets/disable_server_load_buttons_report.md`

## Summary of implementation

Disabled the main toolbar **Load File** and **Load Folder** buttons when the
native desktop file picker is unavailable (`not _is_native_mode()`). This covers
Docker/web/server runs (`CLOUDSCOPE_REMOTE=1`, `CLOUDSCOPE_NATIVE=0`) where
those buttons were already no-ops.

The hamburger menu (recents, Load CSV, Load Sample Data, Manning preset, Clear
recents), **Upload File**, and save buttons are unchanged.

Disabled load buttons show a tooltip: *Local file picker is available in the
desktop app*. `_update_button_states()` re-applies load-button disabled state
after selection/busy refreshes so they are not accidentally re-enabled.

## Tests added or modified

- `test_update_button_states_disables_load_buttons_when_not_native`
- `test_update_button_states_enables_load_buttons_in_native_mode`
- `test_update_button_states_keeps_load_buttons_disabled_after_save_refresh`
- `test_local_path_pickers_enabled_matches_native_mode`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_load_save_view.py
```

## Test results

40 passed in `tests/cloudscope/test_load_save_view.py`.

## Concerns or follow-ups

- Local browser-only runs (`CLOUDSCOPE_REMOTE=0`, `CLOUDSCOPE_NATIVE=0`) also
  disable these buttons; they were no-ops there as well.
- Future server-side user-space folder browsing should re-enable or replace
  these controls explicitly.
