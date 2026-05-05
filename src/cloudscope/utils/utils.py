from __future__ import annotations

from nicegui import app
from nicegui import ui
import webbrowser

def open_external(url: str) -> None:
    """Open a URL in the system browser (native) or new tab (browser)."""
    native = getattr(app, "native", None)
    in_native = getattr(native, "main_window", None) is not None
    
    if in_native:
        webbrowser.open(url)
    else:
        ui.run_javascript(f'window.open("{url}", "_blank")')

