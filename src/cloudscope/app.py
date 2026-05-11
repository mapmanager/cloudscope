"""Application entry point for CloudScope."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from nicegui import app, ui

from acqstore.utils.logging import setup_logging as setup_acqstore_logging
from cloudscope.app_config import AppConfig
from cloudscope.pages.home_page import home_page  # noqa: F401  # registers page route
from cloudscope.utils.logging import get_logger, setup_logging
from nicewidgets.utils.logging import setup_logging as setup_nicewidgets_logging

setup_logging()
setup_nicewidgets_logging()
setup_acqstore_logging()

logger = get_logger(__name__)


_TRUE_VALUES = {'1', 'true', 'yes', 'y', 'on'}
_FALSE_VALUES = {'0', 'false', 'no', 'n', 'off'}


@dataclass(frozen=True, slots=True)
class CloudScopeRunConfig:
    """Runtime configuration for launching CloudScope.

    Args:
        host: Optional host passed to ``ui.run``. ``None`` lets NiceGUI choose
            its local default behavior.
        port: Optional port passed to ``ui.run``. ``None`` lets NiceGUI choose
            its local default behavior.
        native: Whether to run in NiceGUI native/pywebview mode.
        reload: Whether NiceGUI reload mode is enabled.
        remote: Whether the app is running in a remote/server environment.
        storage_secret: NiceGUI storage secret.
    """

    host: str | None
    port: int | None
    native: bool
    reload: bool
    remote: bool
    storage_secret: str

    def ui_run_kwargs(self) -> dict[str, Any]:
        """Return keyword arguments for ``ui.run``.

        Returns:
            Keyword arguments suitable for ``nicegui.ui.run``.
        """
        kwargs: dict[str, Any] = {
            'title': 'CloudScope',
            'reload': self.reload,
            'native': self.native,
            'storage_secret': self.storage_secret,
        }
        if self.host is not None:
            kwargs['host'] = self.host
        if self.port is not None:
            kwargs['port'] = self.port
        return kwargs


def _parse_bool_env(name: str, *, default: bool) -> bool:
    """Parse a boolean environment variable.

    Args:
        name: Environment variable name.
        default: Value returned when the variable is unset.

    Returns:
        Parsed boolean value.

    Raises:
        ValueError: If the environment value is not recognized.
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


def _parse_int_env(name: str) -> int | None:
    """Parse an optional integer environment variable.

    Args:
        name: Environment variable name.

    Returns:
        Parsed integer, or ``None`` when unset.

    Raises:
        ValueError: If the environment value is not an integer.
    """
    raw = os.getenv(name)
    if raw is None or raw.strip() == '':
        return None
    return int(raw)


def get_run_config_from_env() -> CloudScopeRunConfig:
    """Build CloudScope run configuration from environment variables.

    Environment variables:
        CLOUDSCOPE_REMOTE: Treat the app as running on a remote/server host.
        CLOUDSCOPE_NATIVE: Override NiceGUI native mode.
        CLOUDSCOPE_RELOAD: Enable or disable NiceGUI reload mode.
        CLOUDSCOPE_HOST: Explicit NiceGUI host.
        CLOUDSCOPE_PORT: Explicit NiceGUI port.
        PORT: Platform-provided port, preferred over ``CLOUDSCOPE_PORT``.
        CLOUDSCOPE_STORAGE_SECRET: NiceGUI storage secret.

    Returns:
        Runtime configuration for ``ui.run``.
    """
    remote = _parse_bool_env('CLOUDSCOPE_REMOTE', default=False)
    native = _parse_bool_env('CLOUDSCOPE_NATIVE', default=not remote)
    reload = _parse_bool_env('CLOUDSCOPE_RELOAD', default=False)

    host = os.getenv('CLOUDSCOPE_HOST')
    if host is not None and host.strip() == '':
        host = None
    if remote and host is None:
        host = '0.0.0.0'

    port = _parse_int_env('PORT')
    if port is None:
        port = _parse_int_env('CLOUDSCOPE_PORT')
    if remote and port is None:
        port = 8080

    storage_secret = os.getenv('CLOUDSCOPE_STORAGE_SECRET', 'cloudscope-dev-secret')

    return CloudScopeRunConfig(
        host=host,
        port=port,
        native=native,
        reload=reload,
        remote=remote,
        storage_secret=storage_secret,
    )


def configure_native_window(config: CloudScopeRunConfig) -> None:
    """Configure pywebview/native-window behavior when native mode is enabled.

    Args:
        config: Runtime configuration.

    Returns:
        None.
    """
    if not config.native:
        logger.info('Skipping native window configuration because native mode is disabled.')
        return

    app_config = AppConfig.load()
    x, y, w, h = app_config.get_window_rect()
    logger.info(f'initial window rect: x:{x}, y:{y}, w:{w}, h:{h}')

    try:
        app.native.window_args.update({
            'x': x,
            'y': y,
            'width': w,
            'height': h,
            'confirm_close': True,
        })
        logger.info(f'global app.native.window_args: {app.native.window_args}')
    except Exception:
        logger.exception('Failed to configure app.native.window_args')


def main() -> None:
    """Run the CloudScope NiceGUI application."""
    config = get_run_config_from_env()
    logger.info(f'CloudScope run config: {config}')
    configure_native_window(config)
    ui.run(**config.ui_run_kwargs())


if __name__ in {'__main__', '__mp_main__'}:
    main()
