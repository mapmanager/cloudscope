# App smoke test report

## Files changed

- `tests/cloudscope/test_app_smoke.py` (new)
- `tests/cloudscope/test_smoke.py` (removed placeholder)

## Summary of implementation

Added layered smoke coverage for `src/cloudscope/app.py`:

1. **Unit tests** for env parsing (`_parse_bool_env`, `_parse_int_env`), `get_run_config_from_env()`, `CloudScopeRunConfig.ui_run_kwargs()`, `configure_native_window()` no-op path, and `main()` branching (web `ui.run` vs Option C desktop) using mocks.
2. **HTTP subprocess smoke test** that starts `app.py` as a real NiceGUI/uvicorn server on an ephemeral localhost port with `CLOUDSCOPE_NATIVE=0`, polls `GET /`, and asserts HTTP 200 plus `CloudScope` in the response.

The subprocess test strips `PYTEST*` and `NICEGUI_SCREEN*` environment variables before launch so the child process does not enter NiceGUI's pytest/screen-test code path (which requires `NICEGUI_SCREEN_TEST_PORT`).

`app.py` remains in the codecov omit list. The omit is still reasonable for the `if __name__ == '__main__'` / `__mp_main__` blocks, while the testable configuration and `main()` orchestration are covered indirectly via imports and mocks.

### NiceGUI testing options considered

| Approach | CI-safe? | Notes |
|----------|----------|-------|
| **Subprocess + httpx** (chosen for E2E) | Yes | True `app.py` startup; no shared NiceGUI global state with pytest |
| **NiceGUI `user` fixture / ASGI transport** | Yes | Fast in-process simulation; good for page tests; pollutes NiceGUI globals if full pages are opened in the same pytest process |
| **NiceGUI `screen` fixture (Selenium + Chrome)** | Yes on `ubuntu-latest` | Slower; needs `selenium` dev dependency and `--driver Chrome` |
| **`ui.run(native=True)` in pytest** | No | Requires display/pywebview; unsuitable for GitHub Actions |

## Tests added or modified

- Added `tests/cloudscope/test_app_smoke.py` (17 tests)
- Removed `tests/cloudscope/test_smoke.py` (trivial `assert True` placeholder)

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_app_smoke.py -v
uv run pytest tests/cloudscope/test_app_smoke.py tests/cloudscope/test_velocity_pool_view.py::test_velocity_pool_view_initializes_dark_mode_from_constructor -v
```

## Test results

- `tests/cloudscope/test_app_smoke.py`: **17 passed** (~4s including subprocess smoke)
- Cross-test pollution check (app smoke then velocity pool view): **18 passed**

## Concerns or follow-ups

- Subprocess smoke adds ~3–4s per CI run; acceptable for a single end-to-end guard.
- In-process NiceGUI `user` simulation is viable for faster page-level tests but needs careful teardown to avoid breaking headless view tests in the same session.
- Optional future work: add a `/pool` subprocess check or a NiceGUI `user`-based page test in an isolated subprocess if faster feedback is needed without Selenium.
