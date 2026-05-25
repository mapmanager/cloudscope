"""Home-page and view-layout visibility events."""

from __future__ import annotations

from dataclasses import dataclass

from cloudscope.events.base import IntentEvent


@dataclass(frozen=True)
class ResetHomeLayoutIntent(IntentEvent):
    """Request resetting Home page splitters to factory defaults."""


@dataclass(frozen=True)
class SetHomeViewVisibleIntent(IntentEvent):
    """Request changing visibility for a configurable Home page view.

    Args:
        view_id: Stable view id string.
        visible: Desired visibility.
    """

    view_id: str
    visible: bool
