"""Top application bar for CloudScope (NiceGUI ``ui.header``).

Follows the KymFlow ``gui_v2.navigation.build_header`` layout pattern: dense
Quasar header, primary ``ui.row`` with title on the left. Optional actions can
be added on the right later.

Call :func:`build_main_header` at page top level **before** ``ui.footer`` and
before the main scrollable column — same ordering as KymFlow ``HomePage.render``.
"""

from __future__ import annotations

import webbrowser
from typing import Any

from nicegui import app
from nicegui import ui

from cloudscope.app_config import AppConfig
from cloudscope.event_bus import EventBus
from cloudscope.events.theme import ThemeChanged

CLOUDSCOPE_GITHUB_URL = "https://github.com/mapmanager/cloudscope"


def _open_external(url: str) -> None:
    """Open URL in native browser window or web tab.

    KymFlow uses the same behavior so link actions work in both native and web.
    """
    native = getattr(app, "native", None)
    in_native = getattr(native, "main_window", None) is not None
    if in_native:
        webbrowser.open(url)
        return
    ui.run_javascript(f'window.open("{url}", "_blank")')


def build_main_header(
    *,
    title: str = "CloudScope",
    app_config: AppConfig | None = None,
    event_bus: EventBus | None = None,
) -> None:
    """Create the shared page header (layout element, top-level only).

    Mirrors KymFlow's compact header: ``dense`` toolbar, contrasting background,
    single prominent title. Must not be nested inside ``ui.column`` / cards.

    Args:
        title: Left-aligned application title text.
        app_config: When set, adds a light/dark toggle (persisted) before the GitHub link.
        event_bus: Optional page-scoped event bus used to publish theme state changes.
    """
    with ui.header().classes(
        "items-center justify-between bg-gray-900 text-gray-100"
    ).props("dense").style("min-height: 40px; padding: 0 12px;"):
        with ui.row().classes("items-center gap-2 min-w-0"):
            ui.label(title).classes("text-lg font-bold truncate")
        with ui.row().classes("items-center gap-2"):
            if app_config is not None:
                dark_mode_el = ui.dark_mode(value=bool(app_config.data.dark_mode))
                theme_btn = ui.button(
                    icon="light_mode" if app_config.data.dark_mode else "dark_mode",
                    on_click=lambda: _toggle_dark_mode(
                        app_config,
                        dark_mode_el,
                        theme_btn,
                        event_bus=event_bus,
                    ),
                ).props("flat dense round")
                theme_btn.tooltip("Toggle light / dark theme")
            github_icon = ui.image("https://cdn.simpleicons.org/github/ffffff").classes(
                "w-5 h-5 cursor-pointer"
            )
            github_icon.on("click", lambda _: _open_external(CLOUDSCOPE_GITHUB_URL))
            github_icon.tooltip("Open CloudScope GitHub repository")


def _toggle_dark_mode(
    app_config: AppConfig,
    dark_mode_el: Any,
    theme_btn: Any,
    *,
    event_bus: EventBus | None = None,
) -> None:
    """Flip persisted dark mode and publish the new application theme.

    Args:
        app_config: Mutable application configuration.
        dark_mode_el: NiceGUI dark-mode element to update.
        theme_btn: Header theme button whose icon should track the mode.
        event_bus: Optional page-scoped event bus for ``ThemeChanged``.

    Returns:
        None.
    """
    app_config.data.dark_mode = not bool(app_config.data.dark_mode)
    dark_mode_el.value = app_config.data.dark_mode
    theme_btn.props(
        f'icon={"light_mode" if app_config.data.dark_mode else "dark_mode"} flat dense round'
    )
    app_config.save()
    if event_bus is not None:
        event_bus.publish(ThemeChanged(dark_mode=bool(app_config.data.dark_mode)))
