"""pywebview window geometry tracking for Option C desktop."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from cloudscope.utils.logging import get_logger

logger = get_logger(__name__)

Rect = tuple[int, int, int, int]
GetRect = Callable[[], Rect | None]
SetRect = Callable[[int, int, int, int], None]
SaveConfig = Callable[[], None]


class WindowGeometryTracker:
    """Track pywebview window move/resize and update stored geometry.

    Move and resize handlers update in-memory config only. Call
    :meth:`sync_from_window` while the window is still live (for example from
    ``events.closing``), then :meth:`persist` to flush config to disk.

    Args:
        window: pywebview window object created by ``webview.create_window``.
        get_rect: Read current stored geometry, or ``None`` when unset.
        set_rect: Write geometry ``(x, y, w, h)`` into application config.
        save: Optional callback invoked by :meth:`persist`.
    """

    def __init__(
        self,
        window: Any,
        get_rect: GetRect,
        set_rect: SetRect,
        *,
        save: SaveConfig | None = None,
    ) -> None:
        self._window = window
        self._get_rect = get_rect
        self._set_rect = set_rect
        self._save = save
        self._persisted = False

    def attach(self) -> None:
        """Register pywebview move/resize handlers.

        Returns:
            None.
        """
        self._window.events.moved += self._on_moved
        self._window.events.resized += self._on_resized

    def sync_from_window(self) -> None:
        """Read current window geometry into config via ``set_rect``.

        Geometry is only available while the pywebview window instance exists.

        Returns:
            None.
        """
        rect = self._read_live_rect()
        if rect is None:
            logger.debug('Window geometry unavailable; skipping sync')
            return
        x, y, w, h = rect
        self._set_rect(x, y, w, h)

    def persist(self) -> None:
        """Flush in-memory geometry config to disk once.

        Does not read live window geometry. Call :meth:`sync_from_window` first
        when the window is still available.

        Returns:
            None.
        """
        if self._persisted or self._save is None:
            return
        self._persisted = True
        self._save()

    def _read_live_rect(self) -> Rect | None:
        """Return live window geometry, or ``None`` when unavailable.

        Returns:
            Current ``(x, y, w, h)``, or ``None`` when attrs are missing.
        """
        try:
            x = self._window.x
            y = self._window.y
            w = self._window.width
            h = self._window.height
        except AttributeError:
            return None
        if x is None or y is None or w is None or h is None:
            return None
        try:
            return (int(x), int(y), int(w), int(h))
        except (TypeError, ValueError):
            return None

    def _current_rect(self) -> Rect | None:
        """Return stored rect or live window geometry when unset.

        Returns:
            Current ``(x, y, w, h)``, or ``None`` when unavailable.
        """
        stored = self._get_rect()
        if stored is not None:
            return stored
        return self._read_live_rect()

    def _on_moved(self, *_args: object) -> None:
        """Update cached x/y while preserving width/height.

        Args:
            *_args: pywebview event payload (ignored; read window attrs).

        Returns:
            None.
        """
        current = self._current_rect()
        if current is None:
            return
        _x, _y, w, h = current
        live = self._read_live_rect()
        if live is None:
            return
        x, y, _, _ = live
        self._set_rect(x, y, w, h)

    def _on_resized(self, *_args: object) -> None:
        """Update cached width/height while preserving x/y.

        Args:
            *_args: pywebview event payload (ignored; read window attrs).

        Returns:
            None.
        """
        current = self._current_rect()
        if current is None:
            return
        x, y, _w, _h = current
        live = self._read_live_rect()
        if live is None:
            return
        _, _, w, h = live
        self._set_rect(x, y, w, h)
