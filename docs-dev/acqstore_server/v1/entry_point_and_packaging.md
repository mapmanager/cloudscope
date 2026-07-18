# AcqStore Server entry point vs CloudScope NiceGUI packaging

## Current AcqStore Server

Two entry modes share the same API port:

| Mode | Entry | Notes |
|------|-------|-------|
| API only | `python -m acqstore_server` → `app.main_uvicorn()` | FastAPI + uvicorn; no NiceGUI |
| Native | `python -m acqstore_server.desktop` → `app.main_native()` | NiceGUI status UI + same routes; `reload=False`, `gzip_middleware_factory=None` |

```text
uv run python -m acqstore_server
→ acqstore_server/__main__.py
    → multiprocessing.freeze_support()
    → acqstore_server.app.main()   # uvicorn unless ACQSTORE_SERVER_NATIVE=1

uv run python -m acqstore_server.desktop
→ acqstore_server/desktop.py
    → freeze_support + main_native()
```

`if __name__ == '__main__':` guards are required for freeze/pack.

## What CloudScope does (NiceGUI / pywebview)

See `docs-dev/pyinstaller_nicegui_multiprocessing.md` and `src/cloudscope/app.py`:

```python
if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
elif __name__ == '__mp_main__':
    # configure_native_window only — NEVER main() / ui.run()
    ...
```

Rules that matter for AcqStore Server native pack:

1. Always `freeze_support()` under `__main__` before launching.
2. Never call `main()` / `ui.run()` from `__mp_main__`.
3. Packaged NiceGUI requires `reload=False` when frozen.
4. **Never** enable default NiceGUI GZip for this app (binary session GETs).

## Verdict

- API-only and native desktop entries are both supported.
- Pack with `./packaging/acqstore_server/build_app.sh` (includes static demo datas).
- Rebuild the `.app` after native UI / gzip / route changes before distributing.
