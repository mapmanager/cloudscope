"""Application entry point for CloudScope."""

from nicegui import ui

from cloudscope.core.utils.logging import get_logger, setup_logging
from cloudscope.gui.app_config import AppConfig
from cloudscope.gui.home_page import home_page  # noqa: F401  # registers page route

logger = get_logger(__name__)


def main() -> None:
    """Run the CloudScope NiceGUI application."""
    setup_logging()
    app_config = AppConfig.load(create_if_missing=False)
    x, y, w, h = app_config.get_window_rect()
    logger.info(f'loaded appconfig window rect: {(x, y, w, h)}')

    ui.run(
        title='CloudScope',
        reload=False,
        native=True,
        storage_secret='cloudscope-dev-secret',
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
