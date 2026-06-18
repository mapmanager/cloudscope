"""pywebview window geometry tracking for Option C desktop."""

from __future__ import annotations

from typing import Any

from cloudscope.app_config import AppConfig
from cloudscope.utils.logging import get_logger

logger = get_logger(__name__)


class WindowGeometryTracker:
    """Track main-window move/resize and persist geometry to ``AppConfig``.

    Args:
        app_config: Shared application configuration for the desktop process.
        window: pywebview window object created by ``webview.create_window``.
    """

    def __init__(self, app_config: AppConfig, window: Any) -> None:
        self._app_config = app_config
        self._window = window
        self._persisted = False

    def attach(self) -> None:
        """Register pywebview move/resize handlers.

        Returns:
            None.
        """
        self._window.events.moved += self._on_moved
        self._window.events.resized += self._on_resized

    def sync_from_window(self) -> None:
        """Read current window geometry into ``app_config``.

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
        self._app_config.set_window_rect(x, y, w, h)

    def persist(self) -> None:
        """Sync geometry from the window and save config once.

        Returns:
            None.
        """
        if self._persisted:
            return
        self._persisted = True
        self.sync_from_window()
        self._app_config.save()

    def _on_moved(self, *_args: object) -> None:
        """Update cached x/y while preserving width/height.

        Args:
            *_args: pywebview event payload (ignored; read window attrs).

        Returns:
            None.
        """
        x, y, w, h = self._app_config.get_window_rect()
        try:
            x = int(self._window.x)
            y = int(self._window.y)
        except Exception:
            logger.debug('Could not read pywebview window position', exc_info=True)
            return
        self._app_config.set_window_rect(x, y, w, h)

    def _on_resized(self, *_args: object) -> None:
        """Update cached width/height while preserving x/y.

        Args:
            *_args: pywebview event payload (ignored; read window attrs).

        Returns:
            None.
        """
        x, y, w, h = self._app_config.get_window_rect()
        try:
            w = int(self._window.width)
            h = int(self._window.height)
        except Exception:
            logger.debug('Could not read pywebview window size', exc_info=True)
            return
        self._app_config.set_window_rect(x, y, w, h)
