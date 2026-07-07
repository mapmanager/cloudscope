from __future__ import annotations

import webbrowser
from pathlib import Path

from nicegui import app, ui

_NATIVE_WINDOW_DEFAULT_TITLE = 'CloudScope'


def open_external(url: str) -> None:
    """Open a URL in the system browser (native) or new tab (browser)."""
    native = getattr(app, 'native', None)
    in_native = getattr(native, 'main_window', None) is not None

    if in_native:
        webbrowser.open(url)
    else:
        ui.run_javascript(f'window.open("{url}", "_blank")')


def _path_display(path: str) -> str:
    """Shorten absolute paths under the user home to ``~/…`` for display labels.

    Args:
        path: Filesystem path string.

    Returns:
        ``~/…`` when ``path`` resolves under the user home; otherwise ``path``.
    """
    try:
        p = Path(path).expanduser()
        home = Path.home()
        rel = p.resolve(strict=False).relative_to(home.resolve(strict=False))
        return str(Path('~') / rel)
    except (ValueError, OSError, RuntimeError):
        return path


def _format_native_window_title(path: str | None) -> str:
    """Build the NiceGUI native main-window title for a loaded path.

    Args:
        path: Persisted ``last_path`` value, or ``None`` when unset.

    Returns:
        ``CloudScope`` when ``path`` is empty; otherwise
        ``CloudScope — {display path}``.
    """
    if path is None:
        return _NATIVE_WINDOW_DEFAULT_TITLE
    stripped = path.strip()
    if not stripped:
        return _NATIVE_WINDOW_DEFAULT_TITLE
    return f'{_NATIVE_WINDOW_DEFAULT_TITLE} — {_path_display(stripped)}'


def set_native_main_window_title(path: str | None) -> None:
    """Set the NiceGUI single-window native desktop title from a loaded path.

    No-op in browser mode or when ``app.native.main_window`` is unavailable.

    Args:
        path: Persisted ``last_path`` value, or ``None`` when unset.

    Returns:
        None.
    """
    native = getattr(app, 'native', None)
    main_window = getattr(native, 'main_window', None) if native is not None else None
    if main_window is None:
        return
    main_window.set_title(_format_native_window_title(path))
