# 051 — Native status UI: live log, footer, richer open logs

## Files changed

- `src/acqstore_server/gui_defaults.py` — local copy of NiceGUI defaults (**no**
  `nicewidgets` / `cloudscope` import)
- `src/acqstore_server/logging_setup.py` — UI log buffer handler +
  `get_ui_log_text` / `clear_ui_log`
- `src/acqstore_server/status_ui.py` — compact layout, scrollable live log,
  Show health → `logger.info`, footer `name vX · host:port`
- `src/acqstore_server/open_service.py` — richer open INFO (dims, shape, units,
  plane sizes, reference summary)
- `src/acqstore_server/app.py` — native `window_size` `(560, 640)`
- `tests/acqstore_server/test_logging_setup.py` — UI buffer test
- `tests/acqstore_server/test_open_service.py` — open log content
- `tests/acqstore_server/test_native_ui_run_kwargs.py` — window size assert
- `docs-dev/acqstore_server/README.md` — status UI blurb
- `docs-dev/cursor_tickets/051_native_status_ui_live_log_report.md`

## Summary of implementation

- Call local `setUpGuiDefaults('text-xs')` before widgets.
- Removed static “listening”, “Log file:”, and HTML-client hint labels (bind
  info lives in the footer).
- Live log: same `acqstore_server` logger → deque → `ui.scroll_area` + label,
  refreshed on a 0.5 s timer.
- **Show health** fetches `/api/v1/health` and `logger.info`s pretty JSON (no
  browser tab).
- Open success logs header summary for debugging / HTML clients.

## Tests added or modified

- `test_ui_log_buffer_receives_logger_lines`
- `test_open_path_logs_header_summary`
- native window size assert

## Exact test commands run

```bash
uv run pytest tests/acqstore_server/ -q
```

## Test results

**28 passed** (`uv run pytest tests/acqstore_server/ -q`).

## Concerns / follow-ups

- Auto-scroll log to bottom on update (nice-to-have).
- Port-busy UX still separate if needed.

---

## Next ticket sketch — 050 reference overview in 5k HTML

**Goal:** Additive collapsible card with reference plane(s) + scanPath/lineRoi
overlay after Image Display and before Trace Display.

**Collapsible mechanism:** The vendored HTML **already** has plain CSS/JS
`.card.collapsible` / `.collapsed` (not NiceGUI). CloudScope’s home file-list
expansion is NiceGUI `SmartExpansion` — **do not** copy that. Reuse the HTML’s
existing collapsible card pattern (same as box2/box3).

**Content:** Port display logic from `/demo/` (float32 plane → canvas, overlay
`scanPath` or `lineRoi` in reference pixel coords; client-side transpose policy
as documented for demo). Fetch only when `meta.reference != null` after AcqStore
load; hide/collapse when null or TIFF-only load.

**Edit rules:** `ACQSTORE: begin/end 050 …` markers; keep TIFF path unchanged;
ticket report required.
