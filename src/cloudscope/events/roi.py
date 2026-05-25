"""ROI CRUD/edit intents and state."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from cloudscope.events.base import IntentEvent, StateEvent
from cloudscope.state import PrimarySelection


class RoiChangeKind(StrEnum):
    """Supported ROI model mutation kinds."""

    ADD = 'add'
    DELETE = 'delete'
    EDIT = 'edit'


@dataclass(frozen=True)
class AddRoiIntent(IntentEvent):
    """Request creation of a new ROI for a selection snapshot.

    Args:
        selection: File/channel/ROI snapshot captured at user click time.
            ``selection.roi_id`` may be None because the controller creates the
            new ROI.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class DeleteRoiIntent(IntentEvent):
    """Request deletion of an existing ROI.

    Args:
        selection: File/channel/ROI snapshot identifying the ROI to delete.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class BeginEditRoiIntent(IntentEvent):
    """Request entry into ROI edit mode for a selection snapshot.

    Args:
        selection: File/channel/ROI snapshot identifying the ROI to edit.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class CancelEditRoiIntent(IntentEvent):
    """Request cancellation of the current ROI edit mode.

    Args:
        selection: File/channel/ROI snapshot identifying the edited ROI when
            available.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class SubmitEditRoiIntent(IntentEvent):
    """Request submission of ROI edits for a selection snapshot.

    Geometry editing is not implemented in this milestone. The event is kept as
    the controller-facing contract for the toolbar OK action.

    Args:
        selection: File/channel/ROI snapshot identifying the edited ROI.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class ApplyRoiFullWidthIntent(IntentEvent):
    """Request full-width ROI adjustment while editing.

    Args:
        selection: File/channel/ROI snapshot identifying the edited ROI.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class ApplyRoiFullHeightIntent(IntentEvent):
    """Request full-height ROI adjustment while editing.

    Args:
        selection: File/channel/ROI snapshot identifying the edited ROI.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class RoiChanged(StateEvent):
    """Emitted after ROI model state changes for one file.

    The model is authoritative. Views should use this event as a signal to pull
    fresh ROI/table/analysis state from ``AppState`` and the selected
    ``AcqImage``.

    Args:
        operation: ROI mutation kind.
        selection: Selection snapshot after the ROI mutation. For add this
            contains the new ROI id. For delete this contains the next selected
            ROI id, or None when no ROI remains.
        removed_analysis_count: Number of dependent analyses removed because of
            the ROI mutation.
    """

    operation: RoiChangeKind
    selection: PrimarySelection
    removed_analysis_count: int = 0


@dataclass(frozen=True)
class RoiEditModeChanged(StateEvent):
    """Emitted when ROI edit mode starts or ends.

    Args:
        is_editing: True while the app is in ROI edit mode.
        selection: ROI edit selection snapshot, or None when edit mode exits.
        message: User-visible status text.
    """

    is_editing: bool
    selection: PrimarySelection | None
    message: str = ''
