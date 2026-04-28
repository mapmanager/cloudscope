"""
Event definitions for CloudScope.

Events are split into:
- Intent events (user or system requests)
- State events (facts after mutation)
"""

from dataclasses import dataclass


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
class PrimarySelectionChanged(StateEvent):
    """Emitted when (file, channel, roi) selection changes."""
    file_id: str | None
    channel: int | None
    roi_id: int | None


@dataclass(frozen=True)
class MetadataChanged(StateEvent):
    """Emitted after metadata values were applied for one file.

    ``row`` is a shallow snapshot: keys match ``ACQ_FILE_LIST_SCHEMA`` exactly.
    """

    file_id: str
    section_id: str
    row: dict[str, object]