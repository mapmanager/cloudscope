# PyInstaller + NiceGUI + multiprocessing

This document defines the required entry-point pattern for CloudScope when built
with PyInstaller / `nicegui-pack`. It applies to `src/cloudscope/app.py` and any
future packaged NiceGUI entry scripts.

See also:

- `docs-dev/cloudscope_packaging.md`
- `docs-dev/cloudscope_single_window_runtime.md` — single-window native startup,
  `window_args`, and the allowed `__mp_main__` hook

---

## 1. Always use `freeze_support()`

Use the standard Python pattern:

```python
import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
```

This is the approved default implementation for CloudScope.

---

## 2. Never launch the application from `__mp_main__`

Do **not** do this:

```python
if __name__ in {"__main__", "__mp_main__"}:
    main()
```

`__mp_main__` is used by `multiprocessing` child processes. Launching the GUI
from `__mp_main__` can cause a frozen PyInstaller application to recursively
relaunch itself, creating endless copies of the application.

Always use:

```python
if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
```

Launching CloudScope from `__mp_main__` is prohibited.

**Exception (configure only):** single-window native mode may call
`configure_native_window()` from `__mp_main__` so pywebview child processes
receive `app.native.window_args` under macOS spawn. Do **not** call `main()` or
`ui.run()` there. See `docs-dev/cloudscope_single_window_runtime.md`.

---

## 3. For packaged applications, reload must be disabled

Never enable NiceGUI reload mode inside a frozen application.

Recommended pattern when resolving run config:

```python
reload = parse_reload_setting()

if getattr(sys, "frozen", False):
    reload = False
```

PyInstaller builds should always run with `reload=False`. CloudScope sets
`CLOUDSCOPE_RELOAD=0` in `packaging/macos/_config.sh`, and Option C desktop
mode forces `reload=False` in `desktop_launcher.py`.

---

## 4. If recursive relaunch still occurs

The next escalation step is to move `multiprocessing.freeze_support()` earlier
in the file, **before** importing NiceGUI or other modules that may trigger
multiprocessing during import.

Example:

```python
from __future__ import annotations

import multiprocessing

multiprocessing.freeze_support()

from nicegui import ui
```

Only do this if the standard `__main__` guard pattern does not solve the
problem. Do not use this as the default.

---

## 5. Symptoms of missing or incorrect `freeze_support()`

Common symptoms include:

- Multiple copies of the application launching
- Endless application relaunch loops
- New windows appearing repeatedly
- Packaged app behaves differently than source execution
- PyInstaller executable recursively spawning itself

When these symptoms appear, first inspect:

```python
if __name__ == "__main__":
```

and verify:

```python
multiprocessing.freeze_support()
```

is present and that the application is **not** launched from `__mp_main__`.

---

## CloudScope reference implementation

`src/cloudscope/app.py`:

```python
if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
elif __name__ == "__mp_main__":
    configure_native_window(get_run_config_from_env())  # spawn child only
```

Full single-window startup sequence:
`docs-dev/cloudscope_single_window_runtime.md`.

This pattern is required for packaged macOS `.app` builds (`packaging/macos/build_app.sh`)
and for Option C multi-window desktop mode (`desktop_launcher.py`), which calls
`ui.run(native=False)` and creates pywebview windows manually.
