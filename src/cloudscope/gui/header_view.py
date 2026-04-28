"""Top application bar for CloudScope (NiceGUI ``ui.header``).

Follows the KymFlow ``gui_v2.navigation.build_header`` layout pattern: dense
Quasar header, primary ``ui.row`` with title on the left. Optional actions can
be added on the right later.

Call :func:`build_main_header` at page top level **before** ``ui.footer`` and
before the main scrollable column — same ordering as KymFlow ``HomePage.render``.
"""

from __future__ import annotations

import webbrowser

from nicegui import app
from nicegui import ui

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


def build_main_header(*, title: str = "CloudScope") -> None:
    """Create the shared page header (layout element, top-level only).

    Mirrors KymFlow's compact header: ``dense`` toolbar, contrasting background,
    single prominent title. Must not be nested inside ``ui.column`` / cards.

    Args:
        title: Left-aligned application title text.
    """
    with ui.header().classes(
        "items-center justify-between bg-gray-900 text-gray-100"
    ).props("dense").style("min-height: 40px; padding: 0 12px;"):
        with ui.row().classes("items-center gap-2 min-w-0"):
            ui.label(title).classes("text-lg font-bold truncate")
        with ui.row().classes("items-center gap-2"):
            github_icon = ui.image("https://cdn.simpleicons.org/github/ffffff").classes(
                "w-5 h-5 cursor-pointer"
            )
            github_icon.on("click", lambda _: _open_external(CLOUDSCOPE_GITHUB_URL))
            github_icon.tooltip("Open CloudScope GitHub repository")
