"""NiceGUI standalone velocity pool page for CloudScope."""

from __future__ import annotations

from nicegui import ui

from nicewidgets.gui_defaults import setUpGuiDefaults
from cloudscope.runtime import get_current_runtime
from cloudscope.views.footer_view import FooterView
from cloudscope.views.header_view import build_main_header
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
    build_main_header(
        title="CloudScope Velocity Pool",
        app_config=runtime.app_config,
        event_bus=runtime.event_bus,
        show_open_main=True,
    )

    footer = FooterView(
        event_bus=runtime.event_bus,
        app_state=runtime.app_state,
        initially_visible=True,
        show_status=False,
    )
    footer.build()

    pool_view = VelocityPoolView(
        event_bus=runtime.event_bus,
        app_state=runtime.app_state,
        table_font_size_px=int(runtime.app_config.data.table_font_size_px),
        initially_visible=True,
    )
    with ui.column().classes("w-full h-[calc(100vh-4rem-2rem)] min-h-0 p-2"):
        pool_view.build()

    def _on_disconnect() -> None:
        pool_view.on_hide()
        footer.on_hide()

    ui.context.client.on_disconnect(_on_disconnect)
