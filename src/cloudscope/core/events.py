"""
Event definitions for CloudScope.

Events are split into:
- Intent events (user or system requests)
- State events (facts after mutation)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from acqstore.acq_image.acq_image import AcqImage


class Event:
    """Base event."""


class IntentEvent(Event):
    """Base class for intent events."""


class StateEvent(Event):
    """Base class for state events."""


# -----------------------------
# Intent Events
# -----------------------------

@dataclass(frozen=True)
class SelectFileIntent(IntentEvent):
    """Request to select a file."""
    file_id: str | None


@dataclass(frozen=True)
class SelectChannelIntent(IntentEvent):
    """Request to select a channel."""
    channel: int | None


@dataclass(frozen=True)
class SelectRoiIntent(IntentEvent):
    """Request to select an ROI."""
    roi_id: int | None


@dataclass(frozen=True)
class ApplyMetadataIntent(IntentEvent):
    """Request to apply edited metadata for one file section (in-memory only)."""

    file_id: str
    section_id: str
    patch: dict[str, object]


# -----------------------------
# State Events
# -----------------------------

@dataclass(frozen=True)
class FileListChanged(StateEvent):
    """Emitted when the current file list changes."""
    file_ids: list[str]


@dataclass(frozen=True)
class FileSelectionChanged(StateEvent):
    """Emitted when the selected file changes (including initial list load).

    Initial load and file switches publish this event only (not separate
    channel/ROI events); ``channel`` and ``roi_id`` carry the effective defaults
    for the selected file.

    Attributes:
        file_id: Selected file identifier, or ``None`` if nothing is selected.
        acq_image: Resolved ``AcqImage`` when a list is loaded, else ``None``
            (e.g. demo file ids without backend objects).
        channel: Default or current channel for ``file_id``.
        roi_id: Default or current ROI for ``file_id``.
    """

    file_id: str | None
    acq_image: AcqImage | None
    channel: int | None
    roi_id: int | None


@dataclass(frozen=True)
class ChannelSelectionChanged(StateEvent):
    """Emitted when the selected channel changes without a file change.

    Attributes:
        channel: Selected channel index, or ``None`` if cleared.
    """

    channel: int | None


@dataclass(frozen=True)
class RoiSelectionChanged(StateEvent):
    """Emitted when the selected ROI changes without a file change.

    Attributes:
        roi_id: Selected ROI identifier, or ``None`` if cleared.
    """

    roi_id: int | None


@dataclass(frozen=True)
class MetadataChanged(StateEvent):
    """Emitted after metadata values were applied for one file.

    ``row`` is a shallow snapshot: keys match ``ACQ_FILE_LIST_SCHEMA`` exactly.
    """

    file_id: str
    section_id: str
    row: dict[str, object]
