"""
Event definitions for CloudScope.

Events are split into:
- Intent events (user or system requests)
- State events (facts after mutation)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from acqstore.acq_image.acq_image import AcqImage


class Event:
    """Base event."""


class IntentEvent(Event):
    """Base class for intent events."""


class StateEvent(Event):
    """Base class for state events."""


class LoadPathKind(StrEnum):
    """Supported source kinds for load intents."""

    FILE = 'file'
    FOLDER = 'folder'
    CSV = 'csv'


class TaskKind(StrEnum):
    """Supported long-running task categories."""

    LOAD = 'load'
    SAVE = 'save'
    ANALYSIS = 'analysis'


class TaskStatus(StrEnum):
    """Lifecycle states for progress events."""

    QUEUED = 'queued'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


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
    metadata_section_id: str
    patch: dict[str, object]


@dataclass(frozen=True)
class LoadPathIntent(IntentEvent):
    """Request to load files from a path source."""

    path: str
    kind: LoadPathKind
    from_recent: bool = False


@dataclass(frozen=True)
class RemoveRecentPathIntent(IntentEvent):
    """Remove one path from recent files or recent folders (e.g. stale menu pick)."""

    path: str
    kind: LoadPathKind


@dataclass(frozen=True)
class ClearRecentPathsIntent(IntentEvent):
    """Request to clear recent file and folder paths."""


@dataclass(frozen=True)
class SaveSelectedIntent(IntentEvent):
    """Request to save currently selected file."""


@dataclass(frozen=True)
class SaveAllIntent(IntentEvent):
    """Request to save all dirty files."""


# -----------------------------
# State Events
# -----------------------------

@dataclass(frozen=True)
class FileListChanged(StateEvent):
    """Emitted when the current file list changes.

    Attributes:
        file_ids: Stable file identifiers in display order.
        rows: Current table rows keyed by schema field names.
    """
    file_ids: list[str]
    rows: list[dict[str, object]] = field(default_factory=list)


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

    ``file_list_row`` is a shallow snapshot: keys match ``ACQ_FILE_LIST_SCHEMA`` exactly.
    """

    file_id: str
    metadata_section_id: str
    file_list_row: dict[str, object]


@dataclass(frozen=True)
class TaskProgressChanged(StateEvent):
    """Unified progress state for long-running tasks."""

    task_kind: TaskKind
    task_id: str
    task_label: str
    status: TaskStatus
    current: int
    total: int
    message: str


@dataclass(frozen=True)
class AppStatusChanged(StateEvent):
    """Latest app-level status message for footer/notifications."""

    level: StatusLevel
    message: str
    source: StatusSource


@dataclass(frozen=True)
class RecentPathsChanged(StateEvent):
    """Current recent file and folder paths after updates/clear."""

    recent_files: list[str]
    recent_folders: list[str]
