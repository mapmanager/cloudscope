"""Application entry point for CloudScope."""

from nicegui import app, ui

from cloudscope.core.utils.logging import get_logger, setup_logging
from cloudscope.gui.app_config import AppConfig
from cloudscope.gui.home_page import home_page  # noqa: F401  # registers page route

logger = get_logger(__name__)

def _native_init_window_position():
    app_config = AppConfig.load()

    x, y, w, h = app_config.get_window_rect()

    logger.info(f"  initial window rect: x:{x}, y:{y}, w:{w}, h:{h}")
    app.native.window_args.update({
        "x": x,
        "y": y,
        "width": w,
        "height": h,
    })
_native_init_window_position()

# this is REQUIRED here for nicegui-pack (pyinstaller) to work
try:
    app.native.window_args["confirm_close"] = True
    logger.info(f'global app.native.window_args: {app.native.window_args}')
except Exception:
    # Web mode or older NiceGUI internals: ignore safely.
    logger.error('FAILED: app.native.window_args["confirm_close"]')
    pass

def main() -> None:
    """Run the CloudScope NiceGUI application."""
    setup_logging()

    # app_config = AppConfig.load(create_if_missing=False)
    # x, y, w, h = app_config.get_window_rect()
    # logger.info(f'loaded appconfig window rect: {(x, y, w, h)}')

    ui.run(
        title='CloudScope',
        reload=False,
        native=True,
        storage_secret='cloudscope-dev-secret',
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
