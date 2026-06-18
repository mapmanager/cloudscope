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

        Geometry is only available after the GUI loop is running.

        Returns:
            None.
        """
        try:
            x = int(self._window.x)
            y = int(self._window.y)
            w = int(self._window.width)
            h = int(self._window.height)
        except Exception:
            logger.debug('Could not read pywebview window geometry', exc_info=True)
            return
        self._set_rect(x, y, w, h)

    def persist(self) -> None:
        """Sync geometry from the window and save config once.

        Returns:
            None.
        """
        if self._persisted or self._save is None:
            return
        self._persisted = True
        self.sync_from_window()
        self._save()

    def _current_rect(self) -> Rect | None:
        """Return stored rect or live window geometry when unset.

        Returns:
            Current ``(x, y, w, h)``, or ``None`` when unavailable.
        """
        stored = self._get_rect()
        if stored is not None:
            return stored
        try:
            return (
                int(self._window.x),
                int(self._window.y),
                int(self._window.width),
                int(self._window.height),
            )
        except Exception:
            logger.debug('Could not read pywebview window geometry', exc_info=True)
            return None

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
        try:
            x = int(self._window.x)
            y = int(self._window.y)
        except Exception:
            logger.debug('Could not read pywebview window position', exc_info=True)
            return
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
        try:
            w = int(self._window.width)
            h = int(self._window.height)
        except Exception:
            logger.debug('Could not read pywebview window size', exc_info=True)
            return
        self._set_rect(x, y, w, h)
