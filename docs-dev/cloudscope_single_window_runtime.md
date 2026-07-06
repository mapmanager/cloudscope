# CloudScope single-window runtime

This document describes how CloudScope launches and runs in **default
single-window** mode: one NiceGUI app, one primary UI (`/`), shared between
local desktop (`ui.run(native=True)`) and web/remote browser deployment.

It is the operational reference for `src/cloudscope/app.py` startup order,
native window persistence, and what differs between desktop and web shells.

**Out of scope:** Option C multi-window desktop (`desktop_launcher.py`,
`CLOUDSCOPE_MULTI_WINDOW`, separate pywebview windows). That path branches off
before the flow below. See `src/cloudscope/desktop_launcher.py` when needed.

**Related docs:**

- `docs-dev/pyinstaller_nicegui_multiprocessing.md` — `freeze_support()` and
  `__mp_main__` rules for packaged builds
- `docs-dev/cloudscope_packaging.md` — macOS `.app` and Docker deployment ops
- `docs-dev/cloudscope_architecture.md` — MVC / package boundaries

**Historical context:** `docs-dev/codex_tickets/native_single_window_*_report.md`

---

## Mental model

Desktop and web use the **same** application code path after startup branching.
The difference is the **shell**:

| Mode | Shell | Entry |
|------|-------|-------|
| Local desktop (default) | NiceGUI native / pywebview | `uv run python src/cloudscope/app.py` |
| Web / Docker | Browser tab | `docker compose up` (see `docker-compose.yml`) |

Both serve the same `@ui.page("/")` home page and the same per-session
`runtime.py` bootstrap.

```text
app.py main()
  │
  ├─ get_run_config_from_env()
  │
  ├─ should_use_option_c_desktop(config)?
  │     └─ YES → run_option_c_desktop()   [NOT single-window — stop here]
  │
  ├─ configure_native_window(config)      [no-op when native=False]
  │
  └─ ui.run(**config.ui_run_kwargs())
        │
        └─ home_page() → runtime.initialize_once() → HomePage.build()
```

---

## Environment matrix

| Variable | Local desktop (default) | Web / Docker (`docker-compose.yml`) |
|----------|-------------------------|-------------------------------------|
| `CLOUDSCOPE_REMOTE` | `0` (default) | `1` |
| `CLOUDSCOPE_NATIVE` | `1` (default when not remote) | `0` |
| `CLOUDSCOPE_SINGLE_WINDOW` | `1` (default; unset = on) | `1` |
| `CLOUDSCOPE_RELOAD` | `0` (required `0` in packaged `.app`) | `0` |
| `CLOUDSCOPE_HOST` | unset (NiceGUI chooses) | `0.0.0.0` |
| `PORT` / `CLOUDSCOPE_PORT` | unset (NiceGUI chooses) | `8080` |

**Option C opt-in** (not single-window): set `CLOUDSCOPE_MULTI_WINDOW=1` or
`CLOUDSCOPE_DESKTOP_LAUNCHER=option_c`. Default local desktop does **not** use
Option C.

---

## Desktop: `ui.run(native=True)` startup sequence

**Call order matters.** Do not reorder without re-reading NiceGUI native mode
(`nicegui.native.native_mode._open_window`).

### 1. Parent process (`__main__`)

```python
if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
```

1. `get_run_config_from_env()` — build `CloudScopeRunConfig`
2. `should_use_option_c_desktop(config)` — default: `False` → continue
3. **`configure_native_window(config)`** — **before** `ui.run()`
4. **`ui.run(native=True, ...)`** — start NiceGUI server + spawn pywebview child

### 2. `configure_native_window()` (parent and child)

When `config.native` is `True`:

1. Load `AppConfig` via `resolve_user_context(...).load_app_config()`
2. Read saved rect: `x, y, w, h = app_config.get_window_rect()`
3. Update **`app.native.window_args`** (dict merged into `webview.create_window`):

```python
app.native.window_args.update({
    'x': x,
    'y': y,
    'width': w,
    'height': h,
    'confirm_close': True,
})
```

When `config.native` is `False`, this function returns immediately (web mode).

### 3. pywebview child (`__mp_main__`)

On macOS, NiceGUI native mode uses multiprocessing **`spawn`**. The pywebview
child re-imports `src/cloudscope/app.py` as `__mp_main__` before
`webview.create_window`. The child's `app.native.window_args` would otherwise
be empty.

**Allowed pattern** (configure only — never launch the app):

```python
elif __name__ == '__mp_main__':
    configure_native_window(get_run_config_from_env())
```

This repopulates `window_args` in the child so **geometry restore** and
**`confirm_close`** apply at window creation time.

See `docs-dev/pyinstaller_nicegui_multiprocessing.md` for why `main()` and
`ui.run()` must **not** run from `__mp_main__`.

### 4. Page load (`home_page`)

On first `/` visit, `HomePage.build()`:

1. `_install_shutdown_handlers()` — `app.on_shutdown` → `app_config.save()`
2. `_register_native_geometry_handlers()` — when `app.native` exists:
   - `app.native.on('resized', self._native_resize)`
   - `app.native.on('moved', self._native_moved)`

Move/resize update **in-memory** `AppConfig` only. Disk write happens on
shutdown.

---

## `window_args` rules

| Do | Don't |
|----|-------|
| Set `x`, `y`, `width`, `height`, `confirm_close` in `app.native.window_args` **before** `ui.run()` | Pass `window_size=` to `ui.run()` |
| Repeat `configure_native_window()` from `__mp_main__` for spawn | Call `main()` or `ui.run()` from `__mp_main__` |
| Let pywebview apply rect at `create_window` | Restore geometry on `loaded` via `main_window.move()` (causes visible snap) |

`confirm_close: True` is pywebview's native yes/no dialog on window close. It
must be present in `window_args` when the window is created.

---

## Geometry and config persistence

| Phase | What happens | Where |
|-------|----------------|-------|
| **Restore** | Saved rect applied at window creation | `configure_native_window` → `window_args` |
| **Track** | Live move/resize → in-memory rect | `home_page._native_moved` / `_native_resize` |
| **Save** | Flush `AppConfig` to disk | `home_page` shutdown handler |
| **Splitters** | Positions in `AppConfig` during session | `SplitterManager`; same shutdown save |

---

## Web deployment: same app, no native shell

Web and Docker use the **same** `main()` → `ui.run()` path with
`CLOUDSCOPE_REMOTE=1` and `CLOUDSCOPE_NATIVE=0`.

Differences from desktop:

- `configure_native_window()` is skipped (`native=False`)
- No pywebview, no `window_args`, no quit dialog
- `home_page` native handlers no-op (`app.native` guards)
- Browser opens `http://host:port/` (NiceGUI `show` behavior; Docker binds
  `0.0.0.0:8080`)

Canonical env block: `docker-compose.yml` service `cloudscope` /
`cloudscope-dev`.

Shared with desktop:

- `runtime.initialize_once()` — controllers, event bus, `AppConfig`
- Same home page UI and analysis workflow
- `user_context` / demo session storage (remote-specific paths under
  `CLOUDSCOPE_DATA_DIR`)

---

## Shared runtime layer (not native-specific)

| File | Role |
|------|------|
| `src/cloudscope/app.py` | Entry, env config, native `window_args`, spawn hook |
| `src/cloudscope/pages/home_page.py` | UI composition, native geometry handlers, shutdown save |
| `src/cloudscope/runtime.py` | Per-session controllers and state (desktop + web) |
| `src/cloudscope/app_config.py` | Window rect, splitters, persisted settings |
| `src/cloudscope/user_context.py` | Workspace / demo session resolution |

Native window behavior belongs in **`app.py`** (shell config before `ui.run`) and
**`home_page.py`** (session lifecycle). Keep `app.py` free of page UI logic.

`src/cloudscope/desktop_launcher.py` is imported only for the Option C branch
check in `main()`. It is **not** on the default single-window execution path.

---

## Anti-patterns (lessons learned)

Do **not** re-introduce these during native window work:

1. **`ui.run(window_size=...)`** — forbidden; use `window_args` before `ui.run()`
2. **`main()` from `__mp_main__`** — recursive launch / double server risk
3. **Monkeypatch NiceGUI `_open_window`** with nested functions — unpickleable on spawn
4. **Env JSON / custom spawn bridges** — unnecessary while `__mp_main__` +
   `configure_native_window()` works
5. **Post-`loaded` geometry restore** — window flashes at default size then snaps
6. **Duplicating geometry logic** — Option C uses `window_geometry.py`; single-window
   uses NiceGUI `moved`/`resized` events (different APIs; do not force one abstraction
   without refactoring Option C)

---

## Manual verification checklist

**Desktop (`uv run python src/cloudscope/app.py`):**

1. Move and resize the window, quit, relaunch — geometry matches saved position/size
   (no flash at default 800×600 then snap)
2. Close window — native yes/no quit dialog appears
3. Adjust splitters, quit, relaunch — splitter positions restored

**Web (`docker compose up cloudscope`):**

1. App serves on `http://localhost:8080`
2. No native / pywebview log noise for window rect
3. Home page loads and functions as in desktop browser mode

---

## Quick file index

```text
src/cloudscope/app.py              Entry, configure_native_window, main()
src/cloudscope/pages/home_page.py  Native handlers, shutdown persist
src/cloudscope/app_config.py       get_window_rect / set_window_rect / save
src/cloudscope/runtime.py          Shared session bootstrap
src/cloudscope/desktop_launcher.py Option C branch only (default: unused)
docker-compose.yml                 Web deployment env reference
```
