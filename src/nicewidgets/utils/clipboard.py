"""Clipboard helpers for NiceGUI applications."""

from __future__ import annotations

import json

try:
    import pyperclip
except ImportError:  # pragma: no cover - depends on optional runtime package
    pyperclip = None  # type: ignore[assignment]

from nicegui import app, ui

from nicewidgets.utils.logging import get_logger

logger = get_logger(__name__)


def copy_to_clipboard(text: str) -> None:
    """Copy text to the active system or browser clipboard.

    Native NiceGUI desktop windows use ``pyperclip`` so the operating-system
    clipboard is updated directly. Browser sessions use ``navigator.clipboard``
    through NiceGUI JavaScript execution.

    Args:
        text: Text to copy.

    Raises:
        RuntimeError: If the app is running in native mode and ``pyperclip`` is
            not installed.
    """
    native_cfg = getattr(app, "native", None)
    is_native_window = getattr(native_cfg, "main_window", None) is not None

    if is_native_window:
        if pyperclip is None:
            raise RuntimeError("pyperclip is required for native clipboard support")
        pyperclip.copy(text)
        logger.debug("copied text via pyperclip")
        return

    text_literal = json.dumps(text)
    ui.run_javascript(f"navigator.clipboard.writeText({text_literal});")
    logger.debug("copied text via browser clipboard")
