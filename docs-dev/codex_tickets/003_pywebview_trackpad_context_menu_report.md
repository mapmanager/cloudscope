# 003 — pywebview trackpad context menu on Plotly canvas

## Files changed

- `src/nicewidgets/utils/desktop.py` — new home for `is_pywebview_desktop()`
- `src/nicewidgets/utils/clipboard.py` — import desktop helper (re-export)
- `src/nicewidgets/tree_widget/tree_widget.py` — import from `desktop`
- `src/nicewidgets/echart_widget/widget.py` — import from `desktop`
- `src/nicewidgets/raster_viewer/frontend/plotly_context_menu_guards.py` — capture-phase JS for pywebview
- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py` — schedule guard install when desktop
- `tests/nicewidgets/test_desktop_runtime.py` — desktop detection tests (replaces `test_clipboard_desktop.py`)
- `tests/nicewidgets/test_plotly_pywebview_context_menu.py` — guard scheduling/install tests

## Summary of implementation

**Problem:** macOS two-finger secondary tap on the Plotly **canvas** in Option C desktop (pywebview WKWebView) was consumed by Plotly drag/zoom or ROI shape handling. The raster context menu already worked in browser Chrome and on plot margins in desktop.

**Fix:** When `is_pywebview_desktop()` is true, install idempotent capture-phase listeners on the Plotly graph div:

- Block non-primary `pointerdown` / `mouseup` / `mousedown` / `mouseup` from reaching Plotly (`stopImmediatePropagation`)
- `contextmenu` → `preventDefault()` (suppress WKWebView chrome menu; NiceGUI handler still opens Quasar menu)

Browser sessions skip guard installation entirely.

**Desktop detection promoted** from `clipboard.py` to `nicewidgets.utils.desktop` (still re-exported via `clipboard` for compatibility).

## Verified dependency versions (this environment)

| Package | `pyproject.toml` | Installed (`uv pip show`) |
|---------|------------------|---------------------------|
| pywebview | `>=6.2.1` | 6.2.1 |
| nicegui | `>=3.10.0` | 3.10.0 |
| plotly | `>=6.7.0` | 6.7.0 |

## Tests added or modified

**Added**

- `tests/nicewidgets/test_desktop_runtime.py`
- `tests/nicewidgets/test_plotly_pywebview_context_menu.py`

**Removed**

- `tests/nicewidgets/test_clipboard_desktop.py` (superseded by `test_desktop_runtime.py`)

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_desktop_runtime.py tests/nicewidgets/test_plotly_pywebview_context_menu.py -v
uv run pytest tests/nicewidgets/ -q
uv run pytest
```

## Test results

- Focused new tests: **20 passed**
- `tests/nicewidgets/`: **360 passed**
- Full `uv run pytest`: **1217 passed**

## Manual sign-off

Option C desktop (`uv run python src/cloudscope/app.py`) — confirmed 2026-06-22:

- [x] Two-finger tap on plot canvas → raster context menu
- [x] Left-drag zoom box still works

Not explicitly re-checked in this session (browser was OK before fix; mouse right-click was OK before fix):

- [ ] Mouse right-click on plot canvas → menu (unchanged)
- [ ] Wheel zoom unchanged
- [ ] ROI edit mode: two-finger tap → menu preferred over shape drag

Browser (`CLOUDSCOPE_NATIVE=false`) — no regression expected (guards not installed).

## Concerns or follow-ups

- If guards are lost after a full plot DOM rebuild, re-call `_install_pywebview_context_menu_guards` after `set_data` (only if manual QA shows regression).
- `cloudscope/views/load_save_view.py` uses parallel `_is_native_mode()` logic; could import `is_pywebview_desktop` in a follow-up.
- Packaged PyInstaller build should be included in manual QA.
