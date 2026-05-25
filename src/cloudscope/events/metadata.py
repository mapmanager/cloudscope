"""Metadata editing events."""

from __future__ import annotations

from dataclasses import dataclass

from cloudscope.events.base import IntentEvent, StateEvent


@dataclass(frozen=True)
class ApplyMetadataIntent(IntentEvent):
    """Request to apply edited metadata for one file section (in-memory only)."""

    file_id: str
    metadata_section_id: str
    patch: dict[str, object]


@dataclass(frozen=True)
class MetadataChanged(StateEvent):
    """Emitted after metadata values were applied for one file.

    ``file_list_row`` is a shallow snapshot: keys match ``ACQ_FILE_LIST_SCHEMA`` exactly.
    """

    file_id: str
    metadata_section_id: str
    file_list_row: dict[str, object]
