"""Application configuration state-change events."""

from __future__ import annotations

from dataclasses import dataclass

from cloudscope.events.base import StateEvent


@dataclass(frozen=True)
class BlindedAnalysisModeChanged(StateEvent):
    """Emitted when blinded analysis display mode changes."""

    blinded: bool
