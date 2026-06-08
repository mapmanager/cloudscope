# 036 Hide Upload Control In Native Mode Report

## Files changed

- `src/cloudscope/views/load_save_view.py`
- `tests/cloudscope/test_load_save_view.py`
- `docs/codex_tickets/036_hide_upload_in_native_mode_report.md`

## Summary of implementation

- `_build_upload_control()` now early-returns when `_is_native_mode()` is true, before adding CSS or constructing `UploadWidget`.
- Native runs therefore render no browser upload control; users load files via the existing pywebview picker (`Load File` / `Load Folder`).
- Browser/remote runs are unchanged: the compact `UploadWidget` is always built (web server always shows the upload button).
- No behavior change for the rest of the toolbar: `self._upload_widget` stays `None` in native mode, and all upload callbacks already guard on `self._upload_widget is not None`.

## Tests added or modified

- Added `test_build_upload_control_skipped_in_native_mode` in `tests/cloudscope/test_load_save_view.py`, which monkeypatches `app.native` and asserts the upload widget is not created in native mode. The native branch early-returns before any `ui.*` call, so the test needs no NiceGUI client context.
- Existing browser-mode upload tests remain unchanged and continue to cover the web path.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_load_save_view.py
```

## Test results

- `30 passed in 1.01s`
- `ReadLints` found no linter errors in edited files.

## Concerns or follow-ups

- Native drag/drop of acquisition files onto the window is still not implemented (separate concern). This ticket only hides the non-functional browser upload control in native mode.
