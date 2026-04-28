"""Application entry point for CloudScope."""

from nicegui import ui

from cloudscope.gui.home_page import home_page  # noqa: F401  # registers page route


def main() -> None:
    """Run the CloudScope NiceGUI application."""
    ui.run(
        title='CloudScope',
        reload=False,
        native=True,
        storage_secret='cloudscope-dev-secret',
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
