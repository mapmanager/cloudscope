"""File loading, recent paths, and save intents/state."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from cloudscope.events.base import IntentEvent, StateEvent


class LoadPathKind(StrEnum):
    """Supported source kinds for load intents."""

    FILE = 'file'
    FOLDER = 'folder'
    CSV = 'csv'


@dataclass(frozen=True)
class LoadPathIntent(IntentEvent):
    """Request to load files from a path source."""

    path: str
    kind: LoadPathKind
    from_recent: bool = False




@dataclass(frozen=True)
class LoadSampleDataIntent(IntentEvent):
    """Request to download/cache and load a registered AcqStore sample dataset."""

    name: str


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
class RecentPathsChanged(StateEvent):
    """Current recent file and folder paths after updates/clear."""

    recent_files: list[str]
    recent_folders: list[str]
