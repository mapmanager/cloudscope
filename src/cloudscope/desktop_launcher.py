"""Option C desktop launcher for CloudScope multi-window mode."""

from __future__ import annotations

import os
import socket
import threading
import time
from typing import TYPE_CHECKING, Any

from nicegui import app, ui

from cloudscope.pages.home_page import home_page  # noqa: F401
from cloudscope.pages.pool_page import pool_page  # noqa: F401
from cloudscope.app_config import AppConfig
from cloudscope.runtime import (
    clear_process_app_config,
    set_process_app_config,
)
from cloudscope.user_context import resolve_user_context
from cloudscope.desktop.quit_flow import handle_main_window_closing
from cloudscope.utils.logging import get_logger
from cloudscope.window_geometry import WindowGeometryTracker

if TYPE_CHECKING:
    from cloudscope.app import CloudScopeRunConfig

logger = get_logger(__name__)

_TRUE_VALUES = {'1', 'true', 'yes', 'y', 'on'}
_FALSE_VALUES = {'0', 'false', 'no', 'n', 'off'}

POOL_WINDOW_WIDTH = 1000
POOL_WINDOW_HEIGHT = 800
POOL_WINDOW_OFFSET_X = 40
POOL_WINDOW_OFFSET_Y = 40


def _parse_bool_env(name: str, *, default: bool) -> bool:
    """Parse a boolean environment variable.

    Args:
        name: Environment variable name.
        default: Value when unset.

    Returns:
        Parsed boolean.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise ValueError(f'Invalid boolean for {name}: {raw!r}')


def single_window_requested() -> bool:
    """Return whether single-window native mode is active.

    Returns:
        True when ``CLOUDSCOPE_SINGLE_WINDOW`` is unset or enabled, unless
        explicit Option C opt-in env vars are set.
    """
    multi = os.getenv('CLOUDSCOPE_MULTI_WINDOW', '').strip().lower()
    if multi in _TRUE_VALUES:
        return False
    launcher = os.getenv('CLOUDSCOPE_DESKTOP_LAUNCHER', '').strip().lower()
    if launcher in {'option_c', 'option-c', 'c'}:
        return False
    return _parse_bool_env('CLOUDSCOPE_SINGLE_WINDOW', default=True)


def should_use_option_c_desktop(config: CloudScopeRunConfig) -> bool:  # noqa: F821
    """Return whether CloudScope should launch Option C desktop mode.

    Args:
        config: CloudScope run configuration.

    Returns:
        True for local desktop when multi-window Option C is the default path.
    """
    if single_window_requested():
        return False
    if not config.native or config.remote:
        return False
    return True


def option_c_enabled() -> bool:
    """Return whether Option C is enabled via explicit env opt-in.

    Deprecated alias kept for tests and backward compatibility. Default local
    desktop now uses Option C via :func:`should_use_option_c_desktop`.

    Returns:
        True when explicit multi-window env flags are set.
    """
    if single_window_requested():
        return False
    multi = os.getenv('CLOUDSCOPE_MULTI_WINDOW', '').strip().lower()
    if multi in _TRUE_VALUES:
        return True
    launcher = os.getenv('CLOUDSCOPE_DESKTOP_LAUNCHER', '').strip().lower()
    return launcher in {'option_c', 'option-c', 'c'}


class PoolLauncher:
    """Manage the optional desktop pool pywebview window."""

    def __init__(
        self,
        *,
        url_host: str,
        port: int,
        app_config: AppConfig,
        main_window: Any | None = None,
    ) -> None:
        """Initialize launcher state.

        Args:
            url_host: Host used in pywebview window URLs.
            port: NiceGUI server port.
            app_config: Shared application configuration for the desktop process.
            main_window: Main pywebview window used for default pool placement.
        """
        self._url_host = url_host
        self._port = port
        self._app_config = app_config
        self._main_window = main_window
        self.pool_window: Any | None = None

    @property
    def main_window(self) -> Any | None:
        """Return the main CloudScope pywebview window when Option C is active.

        Returns:
            Main pywebview window, or ``None`` before the desktop shell starts.
        """
        return self._main_window

    def open_pool(self) -> None:
        """Open or focus the pool pywebview window.

        Returns:
            None.
        """
        import webview

        if self.pool_window is not None:
            try:
                self.pool_window.show()
                return
            except Exception:
                logger.debug('Pool window show failed; recreating', exc_info=True)
                self.pool_window = None

        pool_url = f'http://{self._url_host}:{self._port}/pool'
        saved_rect = self._app_config.get_pool_window_rect()
        if saved_rect is not None:
            x, y, w, h = saved_rect
        else:
            x, y = self._default_pool_position()
            w, h = POOL_WINDOW_WIDTH, POOL_WINDOW_HEIGHT
        logger.info('Opening pool pywebview window: %s at (%s, %s)', pool_url, x, y)
        self.pool_window = webview.create_window(
            'CloudScope Velocity Pool',
            url=pool_url,
            x=x,
            y=y,
            width=w,
            height=h,
        )

        pool_geometry_tracker = WindowGeometryTracker(
            self.pool_window,
            self._app_config.get_pool_window_rect,
            self._app_config.set_pool_window_rect,
        )
        pool_geometry_tracker.attach()

        def _on_pool_closed() -> None:
            logger.info('Pool window closed')
            self.pool_window = None

        self.pool_window.events.closed += _on_pool_closed

    def _default_pool_position(self) -> tuple[int, int]:
        """Return default pool window top-left position.

        Returns:
            ``(x, y)`` offset from the main window when available.
        """
        if self._main_window is not None:
            try:
                return (
                    int(self._main_window.x) + POOL_WINDOW_OFFSET_X,
                    int(self._main_window.y) + POOL_WINDOW_OFFSET_Y,
                )
            except Exception:
                logger.debug('Could not read main window position for pool offset', exc_info=True)
        return (100 + POOL_WINDOW_OFFSET_X, 100 + POOL_WINDOW_OFFSET_Y)


_pool_launcher: PoolLauncher | None = None


def get_pool_launcher() -> PoolLauncher | None:
    """Return the active pool launcher when Option C is running.

    Returns:
        Pool launcher instance, or ``None`` outside Option C desktop mode.
    """
    return _pool_launcher


def _pick_port(config: CloudScopeRunConfig) -> int:  # noqa: F821
    """Choose a listen port for the Option C NiceGUI server.

    Args:
        config: CloudScope run configuration.

    Returns:
        Port number to bind.
    """
    if config.port is not None:
        return int(config.port)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def _url_host(config: CloudScopeRunConfig) -> str:
    """Return the host name used in pywebview URLs.

    Args:
        config: CloudScope run configuration.

    Returns:
        URL host string.
    """
    explicit = os.getenv('CLOUDSCOPE_URL_HOST', '').strip()
    if explicit:
        return explicit
    return '127.0.0.1'


def _wait_for_server(host: str, port: int, *, timeout_s: float = 30.0) -> None:
    """Wait until the NiceGUI server accepts TCP connections.

    Args:
        host: Bind host.
        port: Bind port.
        timeout_s: Maximum wait time in seconds.

    Raises:
        TimeoutError: If the server does not become ready in time.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            try:
                sock.connect((host, port))
                return
            except OSError:
                time.sleep(0.1)
    raise TimeoutError(f'NiceGUI server not ready on {host}:{port}')


def _run_server_thread(config: CloudScopeRunConfig, host: str, port: int) -> None:
    """Run NiceGUI with ``show=False`` for manual pywebview windows.

    Args:
        config: CloudScope run configuration.
        host: Bind host.
        port: Bind port.

    Returns:
        None.
    """
    kwargs = config.ui_run_kwargs()
    kwargs.update(
        {
            'host': host,
            'port': port,
            'native': False,
            'show': False,
            'reload': False,
        }
    )
    ui.run(**kwargs)


def run_option_c_desktop(config: CloudScopeRunConfig) -> None:
    """Launch CloudScope desktop with separate main and pool pywebview windows.

    Args:
        config: CloudScope run configuration.

    Returns:
        None.
    """
    global _pool_launcher

    import webview

    host = config.host or '127.0.0.1'
    port = _pick_port(config)
    url_host = _url_host(config)

    user_context = resolve_user_context(remote=config.remote, native=False)
    app_config = user_context.load_app_config()
    set_process_app_config(app_config, user_context=user_context)

    x, y, w, h = app_config.get_window_rect()

    server_thread = threading.Thread(
        target=_run_server_thread,
        args=(config, host, port),
        daemon=True,
    )
    server_thread.start()
    _wait_for_server(host, port)

    _pool_launcher = PoolLauncher(url_host=url_host, port=port, app_config=app_config)

    main_url = f'http://{url_host}:{port}/'
    logger.info('Opening main pywebview window: %s', main_url)
    main_window = webview.create_window(
        'CloudScope',
        url=main_url,
        x=x,
        y=y,
        width=w,
        height=h,
        confirm_close=False,
    )
    _pool_launcher._main_window = main_window

    geometry_tracker = WindowGeometryTracker(
        main_window,
        app_config.get_window_rect,
        app_config.set_window_rect,
        save=app_config.save,
    )
    geometry_tracker.attach()

    def _on_main_closing() -> bool:
        return handle_main_window_closing(geometry_tracker)

    def _on_main_closed() -> None:
        logger.info('Main window closed; shutting down Option C desktop')
        launcher = get_pool_launcher()
        if launcher is not None and launcher.pool_window is not None:
            try:
                launcher.pool_window.destroy()
            except Exception:
                logger.debug('Pool window destroy failed', exc_info=True)
            launcher.pool_window = None
        try:
            app.shutdown()
        except Exception:
            logger.debug('NiceGUI shutdown failed', exc_info=True)

    main_window.events.closing += _on_main_closing
    main_window.events.closed += _on_main_closed

    try:
        webview.start()
    finally:
        clear_process_app_config()
        _pool_launcher = None
        try:
            app.shutdown()
        except Exception:
            logger.debug('NiceGUI shutdown failed in finally', exc_info=True)
