# AcqStore Server entry point vs CloudScope NiceGUI packaging

## Current AcqStore Server

v0 entry is FastAPI + uvicorn:

```text
uv run python -m acqstore_server
→ acqstore_server/__main__.py
→ multiprocessing.freeze_support()
→ acqstore_server.app.main()  # uvicorn.run(...)
```

`if __name__ == '__main__':` in `__main__.py` is correct for this model.

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

Rules that matter if/when we nicegui-pack AcqStore Server:

1. Always `freeze_support()` under `__main__` before launching.
2. Never call `main()` from `__mp_main__` (infinite relaunch on macOS spawn).
3. Packaged NiceGUI requires `reload=False` when frozen.
4. The CloudScope `__mp_main__` hook exists for **pywebview window_args**, not for starting the server. A pure uvicorn FastAPI freeze typically does **not** need that hook unless we later wrap a native window around the HTML.

## Verdict for today

- Present `__main__` guard is fine.
- `freeze_support()` is added as cheap insurance for future PyInstaller / nicegui-pack.
- Do not copy CloudScope’s `__mp_main__` launch path into AcqStore Server unless we adopt NiceGUI native UI.
