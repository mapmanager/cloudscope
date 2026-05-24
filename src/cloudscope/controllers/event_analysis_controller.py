"""Controller for AcqImage event CRUD workflows."""

from __future__ import annotations

from dataclasses import dataclass

from acqstore.acq_image.analysis.event_analysis.event_analysis import EventAnalysis, EventType
from acqstore.acq_image.analysis.model import AnalysisKey

from cloudscope.controllers.home_page_controller import HomePageController
from cloudscope.event_bus import EventBus
from cloudscope.events import (
    AcqImageEventsChanged,
    AcqImageEventSelectionChanged,
    AcqImageEventsVisibilityChanged,
    AcqImageEventXRangeSelectedIntent,
    AppStatusChanged,
    ChannelSelectionChanged,
    BeginAddAcqImageEventIntent,
    BeginPlotXRangeSelection,
    CancelAddAcqImageEventIntent,
    CancelPlotXRangeSelection,
    DeleteSelectedAcqImageEventIntent,
    FileSelectionChanged,
    RequestAcqImageEventsRefreshIntent,
    RoiSelectionChanged,
    SelectAcqImageEventIntent,
    SetAcqImageEventsVisibleIntent,
    StatusLevel,
    StatusSource,
)
from cloudscope.state import PrimarySelection

from cloudscope.utils.logging import get_logger
logger = get_logger(__name__)


@dataclass(slots=True)
class EventAnalysisController:
    """Coordinate event CRUD intents and analysis model mutations.

    Args:
        event_bus: Page-scoped event bus.
        home_controller: Controller owning current file/selection state.
    """

    event_bus: EventBus
    home_controller: HomePageController
    selected_event_id: int | None = None
    events_visible: bool = True
    _pending_add_selection: PrimarySelection | None = None

    def bind(self) -> None:
        """Subscribe controller handlers to event-analysis intents."""
        self.event_bus.subscribe(BeginAddAcqImageEventIntent, self._on_begin_add)
        self.event_bus.subscribe(CancelAddAcqImageEventIntent, self._on_cancel_add)
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
        try:
            self._required_selection_values(event.selection)
        except ValueError as exc:
            self._publish_status(str(exc), level=StatusLevel.WARNING)
            return
        self._pending_add_selection = self._copy_selection(event.selection)
        self.event_bus.publish(BeginPlotXRangeSelection(selection=self._pending_add_selection))

    def _on_cancel_add(self, event: CancelAddAcqImageEventIntent) -> None:
        """Cancel pending event creation.

        Args:
            event: Cancel intent.
        """
        _ = event
        self._pending_add_selection = None
        self.event_bus.publish(CancelPlotXRangeSelection())

    def _on_x_range_selected(self, event: AcqImageEventXRangeSelectedIntent) -> None:
        """Create an event from a selected x-range.

        Args:
            event: Selected-range intent from plot view.
        """
        if self._pending_add_selection is None:
            return
        if not self._same_selection(self._pending_add_selection, event.selection):
            logger.warning("Ignoring x-range selected for stale selection")
            return
        try:
            analysis = self._get_or_create_event_analysis(event.selection)
            new_event = analysis.add_rect(event.x0, event.x1, event_type=EventType.USER)
        except Exception as exc:
            self._publish_status(f"Could not add event: {exc}", level=StatusLevel.ERROR)
            return
        self.selected_event_id = int(new_event.id)
        self._pending_add_selection = None
        self.event_bus.publish(CancelPlotXRangeSelection())
        self._publish_events_changed(event.selection)
        self.event_bus.publish(AcqImageEventSelectionChanged(selected_event_id=self.selected_event_id))

    def _on_delete_selected(self, event: DeleteSelectedAcqImageEventIntent) -> None:
        """Delete the selected event.

        Args:
            event: Delete intent.
        """
        _ = event
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
        """Select an event id.

        Args:
            event: Select intent.
        """
        self.selected_event_id = None if event.event_id is None else int(event.event_id)
        self.event_bus.publish(AcqImageEventSelectionChanged(selected_event_id=self.selected_event_id))
        self._publish_events_changed(self.home_controller.state.selection)

    def _on_set_visible(self, event: SetAcqImageEventsVisibleIntent) -> None:
        """Set event overlay visibility.

        Args:
            event: Visibility intent.
        """
        self.events_visible = bool(event.visible)
        self.event_bus.publish(AcqImageEventsVisibilityChanged(visible=self.events_visible))
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
        self._pending_add_selection = None
        self.selected_event_id = None
        self.event_bus.publish(CancelPlotXRangeSelection())
        self.event_bus.publish(AcqImageEventSelectionChanged(selected_event_id=None))
        self._publish_events_changed(self.home_controller.state.selection)

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
        """Return existing event analysis for selection, if present."""
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
            )
        )

    def _publish_status(self, message: str, *, level: StatusLevel) -> None:
        """Publish an app status message."""
        self.event_bus.publish(
            AppStatusChanged(
                level=level,
                message=message,
                source=StatusSource.ANALYSIS,
            )
        )

    @staticmethod
    def _required_selection_values(selection: PrimarySelection) -> tuple[str, int, int]:
        """Return required selection values or raise."""
        if selection.file_id is None:
            raise ValueError("No file selected")
        if selection.channel is None:
            raise ValueError("No channel selected")
        if selection.roi_id is None:
            raise ValueError("No ROI selected")
        return (selection.file_id, int(selection.channel), int(selection.roi_id))

    @staticmethod
    def _copy_selection(selection: PrimarySelection) -> PrimarySelection:
        """Return a copied selection."""
        return PrimarySelection(
            file_id=selection.file_id,
            channel=selection.channel,
            roi_id=selection.roi_id,
        )

    @staticmethod
    def _same_selection(left: PrimarySelection, right: PrimarySelection) -> bool:
        """Return whether two selections identify the same analysis."""
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
