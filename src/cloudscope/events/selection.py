"""Primary file/channel/ROI selection intents and state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from cloudscope.events.base import IntentEvent, StateEvent

if TYPE_CHECKING:
    from acqstore.acq_image.acq_image import AcqImage


# Selection source markers. These identify where a file-selection intent or
# state change originated so views can react differently to their own user
# input versus selection driven from elsewhere. In particular, the file-list
# tree view scrolls a programmatically selected row into view only when the
# selection came from another surface (e.g. a pool plot), never as an echo of
# a click on the tree itself.
SELECTION_SOURCE_EXTERNAL = "external"
"""Default source: selection origin is unspecified/generic external."""

SELECTION_SOURCE_FILE_LIST_TREE = "file_list_tree"
"""Selection originated from a user click in the file-list tree view."""

SELECTION_SOURCE_FILE_LIST_TABLE = "file_list_table"
"""Selection originated from a user click in the legacy flat file-list table."""

SELECTION_SOURCE_VELOCITY_POOL = "velocity_pool"
"""Selection originated from a user click in a pool plot / pool table."""

SELECTION_SOURCE_LOAD = "load"
"""Selection originated from loading a file list (initial/default selection)."""

SELECTION_SOURCE_CHANNEL = "channel"
"""Selection source sentinel for a channel-only change (not a file pick)."""

SELECTION_SOURCE_ROI = "roi"
"""Selection source sentinel for an ROI-only change (not a file pick)."""

SELECTION_SOURCE_REFRESH = "refresh"
"""Selection source sentinel for a view refreshing from cached app state."""


@dataclass(frozen=True)
class SelectFileIntent(IntentEvent):
    """Request to select a file (and optionally a specific analysis row).

    Attributes:
        file_id: Stable file identifier, or ``None`` to clear selection.
        channel: Optional explicit channel to select. When ``None``, the
            controller resolves the file's default channel.
        roi_id: Optional explicit ROI identifier to select. When ``None``,
            the controller resolves the file's default ROI.
        analysis_name: Optional analysis identity component. Set only when
            the intent originates from an analysis-row click in
            :class:`AcqImageListTreeView`. ``None`` for all other paths
            (file-row clicks, legacy table-view clicks, programmatic
            file selection). See
            :class:`cloudscope.state.PrimarySelection.analysis_name` for
            the full contract.
        source: Selection origin marker (one of the ``SELECTION_SOURCE_*``
            constants). Threaded through to :class:`FileSelectionChanged` so
            consuming views can distinguish their own user input from
            selection driven elsewhere. Defaults to
            :data:`SELECTION_SOURCE_EXTERNAL`.
    """

    file_id: str | None
    channel: int | None = None
    roi_id: int | None = None
    analysis_name: str | None = None
    source: str = SELECTION_SOURCE_EXTERNAL


@dataclass(frozen=True)
class SelectChannelIntent(IntentEvent):
    """Request to select a channel."""
    channel: int | None


@dataclass(frozen=True)
class SelectRoiIntent(IntentEvent):
    """Request to select an ROI."""
    roi_id: int | None


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
        analysis_name: Carries the analysis identity component when the
            selection originated from an analysis-row click in
            :class:`AcqImageListTreeView`. ``None`` for all other paths.
            See :class:`cloudscope.state.PrimarySelection.analysis_name`
            for the full contract.
        source: Selection origin marker (one of the ``SELECTION_SOURCE_*``
            constants) carried from the originating :class:`SelectFileIntent`
            or load path. Views use it to decide whether a selection change is
            their own user input or came from elsewhere. Defaults to
            :data:`SELECTION_SOURCE_EXTERNAL`.
    """

    file_id: str | None
    acq_image: AcqImage | None
    channel: int | None
    roi_id: int | None
    analysis_name: str | None = None
    source: str = SELECTION_SOURCE_EXTERNAL


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
