"""Controller for AcqImage event CRUD workflows."""

from __future__ import annotations

from dataclasses import dataclass

from acqstore.acq_image.analysis.event_analysis.event_analysis import EventAnalysis, EventType
from acqstore.acq_image.analysis.model import AnalysisKey

from cloudscope.controllers.home_page_controller import HomePageController
from cloudscope.event_bus import EventBus
from cloudscope.events.acq_image_events import (
    AcqImageEventsChanged,
    AcqImageEventSelectionChanged,
    AcqImageEventXRangeSelectedIntent,
    BeginAddAcqImageEventIntent,
    BeginEditAcqImageEventIntent,
    CancelAddAcqImageEventIntent,
    DeleteSelectedAcqImageEventIntent,
    EventEditMode,
    RequestAcqImageEventsRefreshIntent,
    SelectAcqImageEventIntent,
    SetAcqImageEventsVisibleIntent,
)
from cloudscope.events.analysis import (
    AppBusyChanged,
    BeginPlotXRangeSelection,
    CancelPlotXRangeSelection,
)
from cloudscope.events.selection import (
    ChannelSelectionChanged,
    FileSelectionChanged,
    RoiSelectionChanged,
)
from cloudscope.events.status import AppStatusChanged, StatusLevel, StatusSource
from cloudscope.state import PrimarySelection

from cloudscope.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class EventAnalysisController:
    """Coordinate event CRUD intents and analysis model mutations.

    Args:
        event_bus: Page-scoped event bus.
        home_controller: Controller owning current file/selection state.
        selected_event_id: Current selected event id.
        events_visible: Whether event overlays should be shown.
    """

    event_bus: EventBus
    home_controller: HomePageController
    selected_event_id: int | None = None
    events_visible: bool = True
    _pending_selection: PrimarySelection | None = None
    _edit_mode: EventEditMode = EventEditMode.NONE

    def bind(self) -> None:
        """Subscribe controller handlers to event-analysis intents."""
        self.event_bus.subscribe(BeginAddAcqImageEventIntent, self._on_begin_add)
        self.event_bus.subscribe(BeginEditAcqImageEventIntent, self._on_begin_edit)
        self.event_bus.subscribe(CancelAddAcqImageEventIntent, self._on_cancel_edit)
        self.event_bus.subscribe(AcqImageEventXRangeSelectedIntent, self._on_x_range_selected)
        self.event_bus.subscribe(DeleteSelectedAcqImageEventIntent, self._on_delete_selected)
        self.event_bus.subscribe(SelectAcqImageEventIntent, self._on_select_event)
        self.event_bus.subscribe(SetAcqImageEventsVisibleIntent, self._on_set_visible)
        self.event_bus.subscribe(RequestAcqImageEventsRefreshIntent, self._on_refresh_requested)
        self.event_bus.subscribe(FileSelectionChanged, self._on_primary_selection_changed)
        self.event_bus.subscribe(ChannelSelectionChanged, self._on_primary_selection_changed)
        self.event_bus.subscribe(RoiSelectionChanged, self._on_primary_selection_changed)

    def _on_begin_add(self, event: BeginAddAcqImageEventIntent) -> None:
        """Begin one-shot x-range selection for event creation.

        Args:
            event: Begin-add intent.
        """
        if not self._can_begin_edit_mode(event.selection):
            return
        self._begin_edit_mode(
            EventEditMode.ADD,
            event.selection,
            message="Click and drag in the 2D plot to add an event.",
        )

    def _on_begin_edit(self, event: BeginEditAcqImageEventIntent) -> None:
        """Begin one-shot x-range selection for selected-event editing.

        Args:
            event: Begin-edit intent.
        """
        if self.selected_event_id is None:
            self._publish_status("No event selected", level=StatusLevel.WARNING)
            return
        if not self._can_begin_edit_mode(event.selection):
            return
        analysis = self._get_existing_event_analysis(event.selection)
        if analysis is None:
            self._publish_status("No event analysis for selected event", level=StatusLevel.WARNING)
            return
        try:
            analysis.events.get_required(self.selected_event_id)
        except KeyError:
            self.selected_event_id = None
            self._publish_status("Selected event no longer exists", level=StatusLevel.WARNING)
            self.event_bus.publish(AcqImageEventSelectionChanged(selected_event_id=None))
            self._publish_events_changed(event.selection)
            return
        self._begin_edit_mode(
            EventEditMode.EDIT,
            event.selection,
            message="Click and drag in the 2D plot to update the selected event.",
        )

    def _on_cancel_edit(self, event: CancelAddAcqImageEventIntent) -> None:
        """Cancel pending event creation or editing.

        Args:
            event: Cancel intent.
        """
        _ = event
        if self._edit_mode is EventEditMode.NONE:
            return
        selection = self._pending_selection or self.home_controller.state.selection
        self._clear_edit_mode(message="Event edit cancelled")
        self.event_bus.publish(CancelPlotXRangeSelection())
        self._publish_events_changed(selection)

    def _on_x_range_selected(self, event: AcqImageEventXRangeSelectedIntent) -> None:
        """Create or update an event from a selected x-range.

        Args:
            event: Selected-range intent from plot view.
        """
        if self._edit_mode is EventEditMode.NONE or self._pending_selection is None:
            return
        if not self._same_selection(self._pending_selection, event.selection):
            logger.warning("Ignoring x-range selected for stale selection")
            return
        try:
            analysis = self._get_or_create_event_analysis(event.selection)
            if self._edit_mode is EventEditMode.ADD:
                changed_event = analysis.add_rect(event.x0, event.x1, event_type=EventType.USER)
                self.selected_event_id = int(changed_event.id)
            elif self._edit_mode is EventEditMode.EDIT:
                if self.selected_event_id is None:
                    raise RuntimeError("No selected event to edit")
                changed_event = analysis.update_rect(self.selected_event_id, x0=event.x0, x1=event.x1)
                self.selected_event_id = int(changed_event.id)
            else:
                return
        except Exception as exc:
            self._publish_status(f"Could not update event: {exc}", level=StatusLevel.ERROR)
            self._clear_edit_mode(message="Event edit failed")
            self.event_bus.publish(CancelPlotXRangeSelection())
            self._publish_events_changed(event.selection)
            return
        self._clear_edit_mode(message="Event updated")
        self.event_bus.publish(CancelPlotXRangeSelection())
        self._publish_events_changed(event.selection)
        self.event_bus.publish(AcqImageEventSelectionChanged(selected_event_id=self.selected_event_id))

    def _on_delete_selected(self, event: DeleteSelectedAcqImageEventIntent) -> None:
        """Delete the selected event.

        Args:
            event: Delete intent.
        """
        _ = event
        if self._edit_mode is not EventEditMode.NONE:
            self._publish_status("Cancel event editing before deleting", level=StatusLevel.WARNING)
            return
        if self.selected_event_id is None:
            self._publish_status("No event selected", level=StatusLevel.WARNING)
            return
        selection = self.home_controller.state.selection
        try:
            analysis = self._get_existing_event_analysis(selection)
            if analysis is None:
                return
            analysis.delete_rect(self.selected_event_id)
        except Exception as exc:
            self._publish_status(f"Could not delete event: {exc}", level=StatusLevel.ERROR)
            return
        self.selected_event_id = None
        self._publish_events_changed(selection)
        self.event_bus.publish(AcqImageEventSelectionChanged(selected_event_id=None))

    def _on_select_event(self, event: SelectAcqImageEventIntent) -> None:
        """Select an event id without refreshing table row data.

        Args:
            event: Select intent.
        """
        if self._edit_mode is not EventEditMode.NONE:
            return
        self.selected_event_id = None if event.event_id is None else int(event.event_id)
        self.event_bus.publish(AcqImageEventSelectionChanged(selected_event_id=self.selected_event_id))

    def _on_set_visible(self, event: SetAcqImageEventsVisibleIntent) -> None:
        """Set event overlay visibility.

        Args:
            event: Visibility intent.
        """
        self.events_visible = bool(event.visible)
        self._publish_events_changed(self.home_controller.state.selection)

    def _on_refresh_requested(self, event: RequestAcqImageEventsRefreshIntent) -> None:
        """Publish current event rows for a requested selection.

        Args:
            event: Refresh intent from a view that needs current rows.
        """
        self._publish_events_changed(event.selection)

    def _on_primary_selection_changed(self, event: object) -> None:
        """Refresh event state after file/channel/ROI selection changes.

        Args:
            event: Selection state event that triggered the refresh.
        """
        _ = event
        if self._edit_mode is not EventEditMode.NONE:
            self._clear_edit_mode(message="Event edit cancelled")
            self.event_bus.publish(CancelPlotXRangeSelection())
        self.selected_event_id = None
        self.event_bus.publish(AcqImageEventSelectionChanged(selected_event_id=None))
        self._publish_events_changed(self.home_controller.state.selection)

    def _can_begin_edit_mode(self, selection: PrimarySelection) -> bool:
        """Return whether one-shot event editing can begin.

        Args:
            selection: Requested selection.

        Returns:
            True when editing can begin.
        """
        if self._edit_mode is not EventEditMode.NONE:
            self._publish_status("Finish or cancel the current event edit first", level=StatusLevel.WARNING)
            return False
        try:
            self._required_selection_values(selection)
        except ValueError as exc:
            self._publish_status(str(exc), level=StatusLevel.WARNING)
            return False
        return True

    def _begin_edit_mode(self, mode: EventEditMode, selection: PrimarySelection, *, message: str) -> None:
        """Enter one-shot event add/edit mode.

        Args:
            mode: Edit mode to enter.
            selection: Complete selection snapshot.
            message: Human-readable app-busy message.
        """
        self._edit_mode = mode
        self._pending_selection = self._copy_selection(selection)
        self.event_bus.publish(
            AppBusyChanged(
                is_busy=True,
                task_kind=None,
                task_id=None,
                message=message,
            )
        )
        self.event_bus.publish(BeginPlotXRangeSelection(selection=self._pending_selection))
        self._publish_events_changed(selection)

    def _clear_edit_mode(self, *, message: str) -> None:
        """Leave event add/edit mode and clear app busy state.

        Args:
            message: Human-readable terminal message for busy-state consumers.
        """
        self._edit_mode = EventEditMode.NONE
        self._pending_selection = None
        self.event_bus.publish(
            AppBusyChanged(
                is_busy=False,
                task_kind=None,
                task_id=None,
                message=message,
            )
        )

    def _get_or_create_event_analysis(self, selection: PrimarySelection) -> EventAnalysis:
        """Return or create event analysis for selection.

        Args:
            selection: Complete primary selection.

        Returns:
            Event analysis instance.
        """
        file_id, channel, roi_id = self._required_selection_values(selection)
        acq_image_list = self.home_controller.state.acq_image_list
        if acq_image_list is None:
            raise RuntimeError("No AcqImageList loaded")
        acq_image = acq_image_list.get_file_by_id(file_id)
        if acq_image is None:
            raise RuntimeError(f"Selected file not loaded: {file_id!r}")
        analysis = acq_image.analysis_set.get_or_create(EventAnalysis.analysis_name, channel=channel, roi_id=roi_id)
        if not isinstance(analysis, EventAnalysis):
            raise TypeError(f"Expected EventAnalysis, got {type(analysis).__name__}")
        return analysis

    def _get_existing_event_analysis(self, selection: PrimarySelection) -> EventAnalysis | None:
        """Return existing event analysis for selection, if present.

        Args:
            selection: Current primary selection.

        Returns:
            Existing event analysis, or None.
        """
        try:
            file_id, channel, roi_id = self._required_selection_values(selection)
        except ValueError:
            return None
        acq_image_list = self.home_controller.state.acq_image_list
        if acq_image_list is None:
            return None
        acq_image = acq_image_list.get_file_by_id(file_id)
        if acq_image is None:
            return None
        analysis = acq_image.analysis_set.get(AnalysisKey(EventAnalysis.analysis_name, channel, roi_id))
        return analysis if isinstance(analysis, EventAnalysis) else None

    def _publish_events_changed(self, selection: PrimarySelection) -> None:
        """Publish current event rows for selection.

        Args:
            selection: Selection snapshot.
        """
        analysis = self._get_existing_event_analysis(selection)
        rows = [] if analysis is None else [_event_row(event) for event in analysis.get_rects()]
        self.event_bus.publish(
            AcqImageEventsChanged(
                selection=self._copy_selection(selection),
                rows=rows,
                selected_event_id=self.selected_event_id,
                visible=self.events_visible,
                edit_mode=self._edit_mode,
            )
        )

    def _publish_status(self, message: str, *, level: StatusLevel) -> None:
        """Publish an app status message.

        Args:
            message: Status message.
            level: Status severity.
        """
        self.event_bus.publish(
            AppStatusChanged(
                level=level,
                message=message,
                source=StatusSource.ANALYSIS,
            )
        )

    @staticmethod
    def _required_selection_values(selection: PrimarySelection) -> tuple[str, int, int]:
        """Return required selection values or raise.

        Args:
            selection: Primary selection.

        Returns:
            File id, channel, and ROI id.

        Raises:
            ValueError: If any required field is missing.
        """
        if selection.file_id is None:
            raise ValueError("No file selected")
        if selection.channel is None:
            raise ValueError("No channel selected")
        if selection.roi_id is None:
            raise ValueError("No ROI selected")
        return (selection.file_id, int(selection.channel), int(selection.roi_id))

    @staticmethod
    def _copy_selection(selection: PrimarySelection) -> PrimarySelection:
        """Return a copied selection.

        Args:
            selection: Selection to copy.

        Returns:
            Copied selection.
        """
        return PrimarySelection(
            file_id=selection.file_id,
            channel=selection.channel,
            roi_id=selection.roi_id,
        )

    @staticmethod
    def _same_selection(left: PrimarySelection, right: PrimarySelection) -> bool:
        """Return whether two selections identify the same analysis.

        Args:
            left: First selection.
            right: Second selection.

        Returns:
            True when both selections refer to the same file/channel/ROI.
        """
        return (
            left.file_id == right.file_id
            and left.channel == right.channel
            and left.roi_id == right.roi_id
        )


def _event_row(event: object) -> dict[str, object]:
    """Return a table row for an AcqImage event.

    Args:
        event: Event object.

    Returns:
        Row dictionary.
    """
    event_type = getattr(event, "event_type")
    if hasattr(event_type, "value"):
        event_type = event_type.value
    return {
        "id": str(getattr(event, "id")),
        "event_id": int(getattr(event, "id")),
        "event_type": str(event_type),
        "x0": float(getattr(event, "x0")),
        "x1": float(getattr(event, "x1")),
        "duration": float(getattr(event, "duration")),
    }
