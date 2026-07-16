# 048 — Native mode 15–20 s session GET: NiceGUI default GZip

## Problem

With `uv run python -m acqstore_server.desktop` (NiceGUI native), demo
`?perf=1` showed ~17 s on `fetch.*.http_headers` for each ~20 MB channel, then
~40 ms `arrayBuffer`. API-only `uv run python -m acqstore_server` was ~3 ms
headers / ~20–40 ms total for the same payload.

This looked like event-loop starvation or “native UI vs API” process design.
It was not.

## Who handles a URL request?

Same FastAPI routes on both paths (`register_api_routes` on either
`create_app()` or NiceGUI’s `app`). Sync `def` channel handlers return
`Response(content=bytes)`. Uvicorn serves them.

Difference: **NiceGUI `ui.run()` installs Starlette `GZipMiddleware` by
default** (`compresslevel=9`). API-only uvicorn does not.

Docs: [NiceGUI configuration / `ui.run` / `gzip_middleware_factory`](https://nicegui.io/documentation/section_configuration_deployment).

## Behavior / timing analysis

| Mode | Accept-Encoding | Content-Encoding | ~20 MB real OIR plane |
|------|-----------------|------------------|------------------------|
| API-only | gzip (browser) | none | ~20–40 ms |
| Native (before fix) | gzip | gzip | **~17 s to first header** |
| Native (before fix) | identity | none | ~20 ms |
| Native (after fix) | gzip | none | **~35 ms** |

Mechanism:

1. Browser always sends `Accept-Encoding: gzip`.
2. `GZipMiddleware` **buffers and compresses the full body before sending
   response headers** (explains `http_headers` ≫ `arrayBuffer`).
3. Random float32 compresses in ~0.6 s at level 9.
4. **Real linescan float32** is highly compressible (~20 MB → ~4.4 MB) and
   zlib level 9 spends **~17 s** on that work — matching user timings exactly
   (calcium + vessels ≈ 34 s of header waits).

Not an overcomplicated dual-server design. Not event-loop starvation from the
status window. One middleware default.

## Fix

- `native_ui_run_kwargs(...)` passes `gzip_middleware_factory=None`.
- `main_native()` uses those kwargs for `ui.run`.
- Document in `docs-dev/acqstore_server/README.md`.

No need to split native UI onto a separate port for this bug.

## Files changed

- `src/acqstore_server/app.py` — `native_ui_run_kwargs`, disable gzip
- `tests/acqstore_server/test_native_ui_run_kwargs.py` — regression assert
- `docs-dev/acqstore_server/README.md` — native gzip note
- `docs-dev/cursor_tickets/048_native_gzip_session_fetch_fix_report.md`

## Tests

```bash
uv run pytest tests/acqstore_server/test_native_ui_run_kwargs.py tests/acqstore_server/test_api_v1.py -q
```

Result: **12 passed**.

Manual reproduction (before/after) on
`tmp/Example OCaMP-FITC Data/20260709_A131_0006.oir` under NiceGUI
`native=True`: gzip path **17231 ms → 34.8 ms**.

## Concerns / follow-ups

- Packaged `.app` picks up this fix on next native rebuild.
- If gzip is ever re-enabled for HTML assets only, exclude `/api/v1/session/**`
  (binary planes must not go through level-9 gzip).
- User should re-run desktop demo `?perf=1` and confirm `http_headers` is
  low-ms again.
