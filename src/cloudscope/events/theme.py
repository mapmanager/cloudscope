"""Application theme state events."""

from __future__ import annotations

from dataclasses import dataclass

from cloudscope.events.base import StateEvent


@dataclass(frozen=True)
class ThemeChanged(StateEvent):
    """Published when the application light/dark theme changes.

    Args:
        dark_mode: True when dark mode is enabled.
    """

    dark_mode: bool
