"""NiceGUI standalone velocity pool page for CloudScope."""

from __future__ import annotations

from nicegui import ui

from nicewidgets.gui_defaults import setUpGuiDefaults
from cloudscope.runtime import get_current_runtime
from cloudscope.views.footer_view import FooterView
from cloudscope.views.header_view import build_main_header, enable_page_dark_mode
from cloudscope.views.velocity_pool_view import VelocityPoolView


@ui.page("/pool")
def pool_page() -> None:
    """Render the standalone velocity pool page for the current session.

    Returns:
        None.
    """
    runtime = get_current_runtime()
    runtime.initialize_once()

    setUpGuiDefaults(runtime.app_config.get_attribute("text_size"))
    ui.page_title("CloudScope Velocity Pool")
    theme_subscription = enable_page_dark_mode(runtime.app_config, runtime.event_bus)
    build_main_header(
        title="CloudScope Velocity Pool",
        show_open_main=False,
        show_docs=False,
    )

    footer = FooterView(
        event_bus=runtime.event_bus,
        app_state=runtime.app_state,
        initially_visible=True,
        show_status=False,
        blinded_provider=runtime.app_config.get_blinded,
    )
    footer.build()

    pool_view = VelocityPoolView(
        event_bus=runtime.event_bus,
        app_state=runtime.app_state,
        table_font_size_px=int(runtime.app_config.data.table_font_size_px),
        initially_visible=True,
        dark_mode=bool(runtime.app_config.data.dark_mode),
        dark_mode_provider=lambda: bool(runtime.app_config.data.dark_mode),
        blinded_provider=runtime.app_config.get_blinded,
    )
    with ui.column().classes("w-full h-[calc(100vh-4rem-2rem)] min-h-0 p-2"):
        pool_view.build()

    def _on_disconnect() -> None:
        theme_subscription.unsubscribe()
        pool_view.on_hide()
        footer.on_hide()

    ui.context.client.on_disconnect(_on_disconnect)
