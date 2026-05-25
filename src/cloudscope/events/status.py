"""Application status notifications."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from cloudscope.events.base import StateEvent


class StatusLevel(StrEnum):
    """UI status severity level."""

    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'


class StatusSource(StrEnum):
    """Subsystem source for a status message."""

    LOAD = 'load'
    SAVE = 'save'
    ANALYSIS = 'analysis'
    SYSTEM = 'system'


@dataclass(frozen=True)
class AppStatusChanged(StateEvent):
    """Latest app-level status message for footer/notifications."""

    level: StatusLevel
    message: str
    source: StatusSource
