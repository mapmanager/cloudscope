"""Home-page layout events."""

from __future__ import annotations

from dataclasses import dataclass

from cloudscope.events.base import IntentEvent


@dataclass(frozen=True)
class ResetHomeLayoutIntent(IntentEvent):
    """Request resetting Home page splitters to factory defaults."""
