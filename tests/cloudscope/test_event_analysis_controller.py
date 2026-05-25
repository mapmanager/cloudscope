"""Tests for EventAnalysisController."""

from __future__ import annotations

from dataclasses import dataclass

from acqstore.acq_image.acq_analysis_set import AcqAnalysisSet
from acqstore.acq_image.analysis.event_analysis.event_analysis import EventAnalysis
from cloudscope.controllers.event_analysis_controller import EventAnalysisController
from cloudscope.event_bus import EventBus
from cloudscope.events.acq_image_events import (
    AcqImageEventsChanged,
    AcqImageEventSelectionChanged,
    AcqImageEventXRangeSelectedIntent,
    BeginAddAcqImageEventIntent,
    BeginEditAcqImageEventIntent,
    DeleteSelectedAcqImageEventIntent,
    EventEditMode,
    RequestAcqImageEventsRefreshIntent,
    SelectAcqImageEventIntent,
    SetAcqImageEventsVisibleIntent,
)
from cloudscope.events.analysis import AppBusyChanged, BeginPlotXRangeSelection
from cloudscope.events.selection import FileSelectionChanged
from cloudscope.state import PrimarySelection


class FakeAcqImage:
    """Fake acquisition image with analysis set."""

    def __init__(self) -> None:
        """Initialize fake image."""
        self.analysis_set = AcqAnalysisSet("fake.tif")


class FakeAcqImageList:
    """Fake image list resolving one file id."""

    def __init__(self, acq_image: FakeAcqImage) -> None:
        """Initialize fake image list."""
        self._acq_image = acq_image

    def get_file_by_id(self, file_id: str) -> FakeAcqImage:
        """Return the fake acquisition image."""
        _ = file_id
        return self._acq_image


@dataclass
class FakeState:
    """Fake home-controller state."""

    selection: PrimarySelection
    acq_image_list: FakeAcqImageList


class FakeHomeController:
    """Fake home-page controller."""

    def __init__(self, state: FakeState) -> None:
        """Initialize fake controller."""
        self.state = state


def _make_controller() -> tuple[EventAnalysisController, EventBus, FakeAcqImage, PrimarySelection]:
    """Create a controller fixture.

    Returns:
        Controller, bus, fake image, and selection.
    """
    acq_image = FakeAcqImage()
    selection = PrimarySelection(file_id="file", channel=0, roi_id=1)
    home = FakeHomeController(FakeState(selection=selection, acq_image_list=FakeAcqImageList(acq_image)))
    bus = EventBus()
    controller = EventAnalysisController(bus, home)  # type: ignore[arg-type]
    controller.bind()
    return controller, bus, acq_image, selection


def test_controller_adds_event_from_x_range_and_publishes_state() -> None:
    """Controller should create event after plot range selection."""
    _controller, bus, acq_image, selection = _make_controller()
    begin_events: list[BeginPlotXRangeSelection] = []
    changed_events: list[AcqImageEventsChanged] = []
    selected_events: list[AcqImageEventSelectionChanged] = []
    busy_events: list[AppBusyChanged] = []
    bus.subscribe(BeginPlotXRangeSelection, lambda event: begin_events.append(event))
    bus.subscribe(AcqImageEventsChanged, lambda event: changed_events.append(event))
    bus.subscribe(AcqImageEventSelectionChanged, lambda event: selected_events.append(event))
    bus.subscribe(AppBusyChanged, lambda event: busy_events.append(event))

    bus.publish(BeginAddAcqImageEventIntent(selection=selection))
    bus.publish(AcqImageEventXRangeSelectedIntent(selection=selection, x0=2.0, x1=5.0))

    assert begin_events
    assert busy_events[0].is_busy is True
    assert busy_events[-1].is_busy is False
    analysis = acq_image.analysis_set.get_or_create(EventAnalysis.analysis_name, channel=0, roi_id=1)
    assert isinstance(analysis, EventAnalysis)
    assert len(analysis.get_rects()) == 1
    assert changed_events[-1].rows[0]["event_id"] == 1
    assert changed_events[-1].edit_mode is EventEditMode.NONE
    assert selected_events[-1].selected_event_id == 1


def test_controller_edits_selected_event_from_x_range() -> None:
    """Controller should update selected event after edit range selection."""
    controller, bus, acq_image, selection = _make_controller()
    analysis = acq_image.analysis_set.create(EventAnalysis.analysis_name, channel=0, roi_id=1)
    assert isinstance(analysis, EventAnalysis)
    analysis.add_rect(0.0, 1.0)
    controller.selected_event_id = 1
    changed_events: list[AcqImageEventsChanged] = []
    bus.subscribe(AcqImageEventsChanged, lambda event: changed_events.append(event))

    bus.publish(BeginEditAcqImageEventIntent(selection=selection))
    bus.publish(AcqImageEventXRangeSelectedIntent(selection=selection, x0=10.0, x1=12.5))

    edited = analysis.events.get_required(1)
    assert edited.x0 == 10.0
    assert edited.x1 == 12.5
    assert changed_events[-1].selected_event_id == 1


def test_controller_delete_selected_event() -> None:
    """Controller should delete selected event and clear selection."""
    controller, bus, acq_image, _selection = _make_controller()
    analysis = acq_image.analysis_set.create(EventAnalysis.analysis_name, channel=0, roi_id=1)
    assert isinstance(analysis, EventAnalysis)
    analysis.add_rect(0.0, 1.0)
    controller.selected_event_id = 1
    changed_events: list[AcqImageEventsChanged] = []
    bus.subscribe(AcqImageEventsChanged, lambda event: changed_events.append(event))

    bus.publish(DeleteSelectedAcqImageEventIntent())

    assert analysis.get_rects() == []
    assert changed_events[-1].selected_event_id is None


def test_controller_selection_does_not_republish_rows() -> None:
    """Selection-only intents should not force table row replacement."""
    _controller, bus, _acq_image, _selection = _make_controller()
    changed_events: list[AcqImageEventsChanged] = []
    selected_events: list[AcqImageEventSelectionChanged] = []
    bus.subscribe(AcqImageEventsChanged, lambda event: changed_events.append(event))
    bus.subscribe(AcqImageEventSelectionChanged, lambda event: selected_events.append(event))

    bus.publish(SelectAcqImageEventIntent(event_id=3))

    assert not changed_events
    assert selected_events[-1].selected_event_id == 3


def test_controller_visibility_publishes_single_snapshot_state() -> None:
    """Controller should publish visibility through the events snapshot."""
    _controller, bus, _acq_image, _selection = _make_controller()
    changed_events: list[AcqImageEventsChanged] = []
    bus.subscribe(AcqImageEventsChanged, lambda event: changed_events.append(event))

    bus.publish(SetAcqImageEventsVisibleIntent(visible=False))

    assert changed_events[-1].visible is False


def test_controller_refresh_request_publishes_current_rows() -> None:
    """Controller should publish existing event rows for a requested selection."""
    _controller, bus, acq_image, selection = _make_controller()
    analysis = acq_image.analysis_set.create(EventAnalysis.analysis_name, channel=0, roi_id=1)
    assert isinstance(analysis, EventAnalysis)
    analysis.add_rect(2.0, 4.0)
    changed_events: list[AcqImageEventsChanged] = []
    bus.subscribe(AcqImageEventsChanged, lambda event: changed_events.append(event))

    bus.publish(RequestAcqImageEventsRefreshIntent(selection=selection))

    assert changed_events[-1].rows[0]["event_id"] == 1
    assert changed_events[-1].rows[0]["x0"] == 2.0


def test_controller_selection_change_refreshes_rows_and_clears_selection() -> None:
    """Controller should refresh event rows when primary file selection changes."""
    controller, bus, acq_image, _selection = _make_controller()
    analysis = acq_image.analysis_set.create(EventAnalysis.analysis_name, channel=0, roi_id=1)
    assert isinstance(analysis, EventAnalysis)
    analysis.add_rect(0.0, 1.0)
    controller.selected_event_id = 1
    changed_events: list[AcqImageEventsChanged] = []
    selected_events: list[AcqImageEventSelectionChanged] = []
    bus.subscribe(AcqImageEventsChanged, lambda event: changed_events.append(event))
    bus.subscribe(AcqImageEventSelectionChanged, lambda event: selected_events.append(event))

    bus.publish(FileSelectionChanged(file_id="file", acq_image=acq_image, channel=0, roi_id=1))

    assert selected_events[-1].selected_event_id is None
    assert changed_events[-1].rows[0]["event_id"] == 1
