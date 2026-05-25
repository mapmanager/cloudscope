"""Event-analysis CRUD/select/visibility/edit-mode events."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from cloudscope.events.base import IntentEvent, StateEvent
from cloudscope.state import PrimarySelection


class EventEditMode(StrEnum):
    """Event-analysis edit modes for one-shot x-range workflows."""

    NONE = 'none'
    ADD = 'add'
    EDIT = 'edit'


@dataclass(frozen=True)
class BeginAddAcqImageEventIntent(IntentEvent):
    """Request one-shot x-range selection to create an AcqImage event.

    Args:
        selection: Selection snapshot for the target event analysis.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class BeginEditAcqImageEventIntent(IntentEvent):
    """Request one-shot x-range selection to edit the selected event.

    Args:
        selection: Selection snapshot for the target event analysis.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class CancelAddAcqImageEventIntent(IntentEvent):
    """Request cancellation of pending AcqImage event creation or editing."""


@dataclass(frozen=True)
class AcqImageEventXRangeSelectedIntent(IntentEvent):
    """Report a user-selected x-range for event creation.

    Args:
        selection: Selection snapshot associated with the plotted analysis.
        x0: First x coordinate.
        x1: Second x coordinate.
    """

    selection: PrimarySelection
    x0: float
    x1: float


@dataclass(frozen=True)
class DeleteSelectedAcqImageEventIntent(IntentEvent):
    """Request deletion of the selected AcqImage event."""


@dataclass(frozen=True)
class SelectAcqImageEventIntent(IntentEvent):
    """Request selection of an AcqImage event.

    Args:
        event_id: Event id to select, or None to clear selection.
    """

    event_id: int | None


@dataclass(frozen=True)
class SetAcqImageEventsVisibleIntent(IntentEvent):
    """Request event overlay visibility change.

    Args:
        visible: True to show event overlays.
    """

    visible: bool


@dataclass(frozen=True)
class RequestAcqImageEventsRefreshIntent(IntentEvent):
    """Request current AcqImage event rows for one selection.

    Views emit this when a selection changes or when a hidden event view is
    shown again. The controller remains the only object that reads the
    AcqImage event analysis and publishes table/overlay state.

    Args:
        selection: Selection snapshot to refresh.
    """

    selection: PrimarySelection


@dataclass(frozen=True)
class AcqImageEventsChanged(StateEvent):
    """Emitted after AcqImage event state changes.

    Args:
        selection: Selection snapshot for the event analysis.
        rows: Table rows representing current events.
        selected_event_id: Selected event id, if any.
        visible: Whether plot overlays should be visible.
        edit_mode: Current one-shot edit mode.
    """

    selection: PrimarySelection
    rows: list[dict[str, object]] = field(default_factory=list)
    selected_event_id: int | None = None
    visible: bool = True
    edit_mode: EventEditMode = EventEditMode.NONE


@dataclass(frozen=True)
class AcqImageEventSelectionChanged(StateEvent):
    """Emitted when selected AcqImage event id changes.

    Args:
        selected_event_id: Selected event id, if any.
    """

    selected_event_id: int | None
