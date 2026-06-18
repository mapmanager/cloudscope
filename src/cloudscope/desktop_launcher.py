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
from cloudscope.runtime import get_current_runtime
from cloudscope.user_context import resolve_user_context
from cloudscope.utils.logging import get_logger

if TYPE_CHECKING:
    from cloudscope.app import CloudScopeRunConfig

logger = get_logger(__name__)

_TRUE_VALUES = {'1', 'true', 'yes', 'y', 'on'}


class PoolLauncher:
    """Manage the optional desktop pool pywebview window."""

    def __init__(self, *, url_host: str, port: int) -> None:
        """Initialize launcher state.

        Args:
            url_host: Host used in pywebview window URLs.
            port: NiceGUI server port.
        """
        self._url_host = url_host
        self._port = port
        self.pool_window: Any | None = None

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
        logger.info('Opening pool pywebview window: %s', pool_url)
        self.pool_window = webview.create_window('CloudScope Velocity Pool', url=pool_url)

        def _on_pool_closed() -> None:
            logger.info('Pool window closed')
            self.pool_window = None

        self.pool_window.events.closed += _on_pool_closed


_pool_launcher: PoolLauncher | None = None


def option_c_enabled() -> bool:
    """Return whether Option C multi-window desktop mode is enabled.

    Returns:
        True when ``CLOUDSCOPE_MULTI_WINDOW`` or ``CLOUDSCOPE_DESKTOP_LAUNCHER=option_c``.
    """
    multi = os.getenv('CLOUDSCOPE_MULTI_WINDOW', '').strip().lower()
    if multi in _TRUE_VALUES:
        return True
    launcher = os.getenv('CLOUDSCOPE_DESKTOP_LAUNCHER', '').strip().lower()
    return launcher in {'option_c', 'option-c', 'c'}


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
    _pool_launcher = PoolLauncher(url_host=url_host, port=port)

    user_context = resolve_user_context(remote=config.remote, native=False)
    app_config = user_context.load_app_config()
    x, y, w, h = app_config.get_window_rect()

    server_thread = threading.Thread(
        target=_run_server_thread,
        args=(config, host, port),
        daemon=True,
    )
    server_thread.start()
    _wait_for_server(host, port)

    main_url = f'http://{url_host}:{port}/'
    logger.info('Opening main pywebview window: %s', main_url)
    main_window = webview.create_window(
        'CloudScope',
        url=main_url,
        x=x,
        y=y,
        width=w,
        height=h,
    )

    def _persist_window_rect() -> None:
        try:
            runtime = get_current_runtime()
            runtime.app_config.save()
        except Exception:
            logger.debug('Skipping runtime save on Option C shutdown', exc_info=True)

    def _on_main_closed() -> None:
        logger.info('Main window closed; shutting down Option C desktop')
        launcher = get_pool_launcher()
        if launcher is not None and launcher.pool_window is not None:
            try:
                launcher.pool_window.destroy()
            except Exception:
                logger.debug('Pool window destroy failed', exc_info=True)
            launcher.pool_window = None
        _persist_window_rect()
        try:
            app.shutdown()
        except Exception:
            logger.debug('NiceGUI shutdown failed', exc_info=True)

    main_window.events.closed += _on_main_closed

    try:
        webview.start()
    finally:
        try:
            app.shutdown()
        except Exception:
            logger.debug('NiceGUI shutdown failed in finally', exc_info=True)
