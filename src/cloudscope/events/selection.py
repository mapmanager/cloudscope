"""Primary file/channel/ROI selection intents and state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from cloudscope.events.base import IntentEvent, StateEvent

if TYPE_CHECKING:
    from acqstore.acq_image.acq_image import AcqImage


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
    """

    file_id: str | None
    channel: int | None = None
    roi_id: int | None = None
    analysis_name: str | None = None


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
    """

    file_id: str | None
    acq_image: AcqImage | None
    channel: int | None
    roi_id: int | None
    analysis_name: str | None = None


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
