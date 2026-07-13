"""Application entry point for CloudScope."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import multiprocessing

from nicegui import app, ui

from acqstore.utils.logging import setup_logging as setup_acqstore_logging
from cloudscope.pages.home_page import home_page  # noqa: F401  # registers page route
from cloudscope.pages.pool_page import pool_page  # noqa: F401  # registers page route
from cloudscope.user_context import resolve_user_context
from cloudscope.devtools.mvc_telemetry import is_mvc_telemetry_enabled
from cloudscope.utils.logging import attach_file_handler_to_loggers, get_logger, setup_logging
from nicewidgets.utils.logging import setup_logging as setup_nicewidgets_logging

setup_logging(level='DEBUG')
setup_nicewidgets_logging(level='DEBUG', file=False)
setup_acqstore_logging(level='DEBUG', file=False)
attach_file_handler_to_loggers('acqstore', 'nicewidgets')

logger = get_logger(__name__)

if is_mvc_telemetry_enabled():
    from cloudscope.devtools.mvc_diagnostics_view import register_mvc_diagnostics_page

    register_mvc_diagnostics_page()



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
        show: Whether NiceGUI should open a browser tab on startup.
    """

    host: str | None
    port: int | None
    native: bool
    reload: bool
    remote: bool
    storage_secret: str
    show: bool

    def ui_run_kwargs(self) -> dict[str, Any]:
        """Return keyword arguments for ``ui.run``.

        Returns:
            Keyword arguments suitable for ``nicegui.ui.run``.
        """

        icon_path = 'src/cloudscope/assets/icons/cloudscope.png'

        kwargs: dict[str, Any] = {
            'title': 'CloudScope',
            'reload': self.reload,
            'native': self.native,
            'storage_secret': self.storage_secret,
            'show': self.show,

            # 1. This handles the browser favicon for web mode
            'favicon': icon_path,
            
            # 2. This handles the desktop window icon for native mode
            # 'window_args': {
            #     'icon': icon_path
            # }
                    }
        if self.host is not None:
            kwargs['host'] = self.host
        if self.port is not None:
            kwargs['port'] = self.port
        return kwargs

# abb google analytics on 20260713
GOOGLE_ANALYTICS_MEASUREMENT_ID = 'G-8057JCR6M8'

def configure_google_analytics(config: CloudScopeRunConfig) -> None:
    """Configure Google Analytics for the remotely hosted web application.

    Analytics is intentionally disabled for local and native desktop modes.

    Args:
        config: Runtime configuration.

    Returns:
        None.
    """
    if not config.remote or config.native:
        logger.info(
            'Skipping Google Analytics: remote=%s native=%s',
            config.remote,
            config.native,
        )
        return

    measurement_id = GOOGLE_ANALYTICS_MEASUREMENT_ID
    ui.add_head_html(
        f"""
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag() {{ dataLayer.push(arguments); }}
  gtag('js', new Date());
  gtag('config', '{measurement_id}');
</script>
""",
        shared=True,
    )
    logger.info('Configured Google Analytics: %s', measurement_id)

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
        CLOUDSCOPE_SHOW: Open a browser tab on startup (default: off when remote).

    Returns:
        Runtime configuration for ``ui.run``.
    """
    remote = _parse_bool_env('CLOUDSCOPE_REMOTE', default=False)
    native = _parse_bool_env('CLOUDSCOPE_NATIVE', default=not remote)
    reload = _parse_bool_env('CLOUDSCOPE_RELOAD', default=False)
    show = _parse_bool_env('CLOUDSCOPE_SHOW', default=not remote)

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
        show=show,
    )


def configure_native_window(config: CloudScopeRunConfig) -> None:
    """Configure pywebview/native-window behavior when native mode is enabled.

    Populates ``app.native.window_args`` before ``ui.run()`` so NiceGUI passes
    them to ``webview.create_window`` in the pywebview child process.

    Args:
        config: Runtime configuration.

    Returns:
        None.
    """
    if not config.native:
        logger.info('Skipping native window configuration because native mode is disabled.')
        return

    user_context = resolve_user_context(remote=config.remote, native=config.native)
    app_config = user_context.load_app_config()
    x, y, w, h = app_config.get_window_rect()
    logger.info('initial window rect: x:%s, y:%s, w:%s, h:%s', x, y, w, h)

    try:
        app.native.window_args.update({
            'x': x,
            'y': y,
            'width': w,
            'height': h,
            'confirm_close': True,
        })
        logger.info('global app.native.window_args: %s', app.native.window_args)
    except Exception:
        logger.exception('Failed to configure app.native.window_args')


def main() -> None:
    """Run the CloudScope NiceGUI application."""
    config = get_run_config_from_env()
    logger.info('CloudScope run config: %s', config)
    from cloudscope.desktop_launcher import run_option_c_desktop, should_use_option_c_desktop

    if should_use_option_c_desktop(config):
        logger.info('Starting CloudScope in Option C multi-window desktop mode')
        run_option_c_desktop(config)
        return
    configure_google_analytics(config)  # abb google analytics 20260713
    configure_native_window(config)
    ui.run(**config.ui_run_kwargs())


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
elif __name__ == '__mp_main__':
    # macOS spawn: pywebview child re-imports this module before _open_window.
    # Populate window_args here only — never call main() or ui.run() from __mp_main__.
    configure_native_window(get_run_config_from_env())
