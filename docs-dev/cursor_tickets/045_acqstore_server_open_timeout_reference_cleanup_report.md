# 045 — AcqStore Server open offload, timeout, reference URL cleanup

## Files changed

- `src/acqstore_server/routes.py` — `asyncio.to_thread` for pick + open; soft
  `load_timeout` (default 120s, env `ACQSTORE_SERVER_OPEN_TIMEOUT_S`); removed
  `GET …/reference/plane`
- `src/acqstore_server/open_service.py` — dropped top-level `reference.url`
- `src/acqstore_server/schemas.py` — `ReferenceMeta` without `url`
- `src/acqstore_server/static/demo/index.html` — fetch only `reference.channels[]`
- `tests/acqstore_server/test_api_v1.py` — channel endpoint, plane 404, timeout test
- `tests/acqstore_server/test_open_service.py` — assert no top-level reference url
- `docs-dev/acqstore_server/html_integration_v0.md`
- `docs-dev/acqstore_server/reference_api_v0.md` (new)
- `docs-dev/acqstore_server/README.md`
- `docs-dev/cursor_tickets/045_acqstore_server_open_timeout_reference_cleanup_report.md`

## Summary of implementation

1. **Event-loop offload:** native picker and `open_path` run in `asyncio.to_thread`
   so long OIR/CZI loads do not block other HTTP handlers.
2. **Soft timeout:** after a path is known, open/decode aborts wait after 120s
   (override with `ACQSTORE_SERVER_OPEN_TIMEOUT_S`) and returns
   `{ ok: false, error: "load_timeout" }` with HTTP **504**. Mid-decode cancel
   is not guaranteed (worker may finish in the background).
3. **No compatibility aliases:** deleted `/reference/plane`; removed top-level
   `reference.url`. Clients must use `reference.channels[i].url`.
4. **Docs:** added focused reference API page for HTML authors.

## Tests added or modified

- `test_open_load_timeout`
- `test_reference_channel_endpoint` (renamed/replaced plane test)
- OpenAPI asserts plane path absent
- Multi-channel open_service assert `'url' not in ref`

## Exact test commands run

```bash
uv run pytest tests/acqstore_server/ -v
```

## Test results

**26 passed**

## Concerns or follow-ups

- **AcqImage sidecar + reference header JSON:** hold for a quick ticket on
  `main` (export tool needs it); keep working server features on this branch.
- Soft timeout does not kill the worker thread mid-`AcqImage` load.
- Optional later: job/poll API if 120s is still insufficient for huge files.
- Policy reminder: **no backward compatibility** in `acqstore_server` unless
  explicitly requested and verified.
