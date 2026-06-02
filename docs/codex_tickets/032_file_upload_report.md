# Ticket 032: File Upload

## Files changed

- `src/acqstore/upload_store.py`
- `src/nicewidgets/upload_widget/__init__.py`
- `src/nicewidgets/upload_widget/normalize.py`
- `src/nicewidgets/upload_widget/upload_widget.py`
- `src/cloudscope/views/load_save_view.py`
- `tests/acqstore/test_upload_store.py`
- `tests/nicewidgets/test_upload_widget.py`
- `tests/cloudscope/test_load_save_view.py`
- `docs/codex_tickets/032_file_upload_report.md`

## Summary of implementation

- Added an AcqStore backend upload persistence helper that stores uploaded acquisition files under `CLOUDSCOPE_UPLOAD_DIR` or `platformdirs.user_data_dir("cloudscope") / "uploads"` with server-side filename and extension validation against the AcqStore runtime import-extension registry. Existing target filenames are rejected with `UploadCollisionError`; uploads never silently overwrite.
- Added a reusable `nicewidgets.upload_widget` package that normalizes NiceGUI upload objects (large temp-file path, in-memory `_data`, async `read`/`save`) into filesystem paths, preserves the browser-provided original filename for callers, and supports an optional debounce flush for environments without `on_multi_upload`.
- Made the upload widget host-friendly: added `show_inline_status`, `extra_props`, `extra_classes`, and `reset_after_batch` constructor flags. The widget now always emits a terminal `on_progress(1.0, ...)` event (with `'Cancelled'` on the cancel path) so external progress UIs can close deterministically. Cooperative cancellation can be reset with `reset_cancel()` so the same widget instance can accept a follow-up upload.
- Mounted the upload widget inline in the CloudScope load/save toolbar in compact mode (drop target + click-to-pick) instead of opening a wrapper dialog. Drag-and-drop onto the toolbar is now native via Quasar's uploader. After a successful or cancelled batch the inner upload's queue is reset.
- Added a persistent server-side progress dialog (`Cancel` button, status label, spinner) opened on the first widget progress event and closed on terminal completion, error, or cancel. The dialog's Cancel button cancels the upload widget and closes the dialog; the existing `LoadPathIntent(kind=FILE)` flow takes over for the actual file load on success.
- Extracted the post-upload persistence logic into `_handle_upload_paths` so the success/collision/unsupported-extension branches are unit-testable without mounting NiceGUI elements.

## Tests added or modified

- Added `tests/acqstore/test_upload_store.py`.
- Added `tests/nicewidgets/test_upload_widget.py`.
- Extended `tests/cloudscope/test_load_save_view.py` with regression coverage for `_accepted_upload_extensions`, `_handle_upload_paths` success, collision, and unsupported-extension paths.
- Re-ran the existing load/save controller and view tests as a regression sanity check.

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_upload_store.py tests/nicewidgets/test_upload_widget.py tests/cloudscope/test_load_save_view.py tests/cloudscope/test_load_save_controller.py
```

## Test results

- 79 passed.

## Concerns or follow-ups

- Cancel cancels server-side post-upload work (file copy + load intent publication) only; it cannot abort the browser → server transfer, which is already complete by the time NiceGUI fires our callbacks.
- NiceGUI does not expose Quasar's per-byte upload progress events, so the dialog shows textual stages (`Upload received` → `Normalizing file 1/1` → `Storing <filename>…`) with a spinner rather than a percentage bar.
- Uploads persist indefinitely in the configured upload directory; no retention/cleanup policy is implemented.
- No server-side upload size limit is enforced in this ticket. Quasar's `max-file-size` would only enforce on the client.
- This ticket implements single acquisition-file uploads only; multi-file upload, folder upload, and sidecar upload remain out of scope.
- Compact uploader styling is achieved with a CSS class (`cloudscope-upload-compact`) that hides Quasar's queue list and tightens header padding. If Quasar is upgraded, the selectors in `_UPLOAD_COMPACT_CSS` may need to be revisited.
