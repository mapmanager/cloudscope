"""Tests for EventAnalysisController."""

from __future__ import annotations

from dataclasses import dataclass

from acqstore.acq_image.acq_analysis_set import AcqAnalysisSet
from acqstore.acq_image.analysis.event_analysis.event_analysis import EventAnalysis
from cloudscope.controllers.event_analysis_controller import EventAnalysisController
from cloudscope.event_bus import EventBus
from cloudscope.events import (
    AcqImageEventsChanged,
    AcqImageEventSelectionChanged,
    AcqImageEventXRangeSelectedIntent,
    BeginAddAcqImageEventIntent,
    BeginPlotXRangeSelection,
    DeleteSelectedAcqImageEventIntent,
    FileSelectionChanged,
    RequestAcqImageEventsRefreshIntent,
    SetAcqImageEventsVisibleIntent,
)
from cloudscope.state import PrimarySelection


class FakeAcqImage:
    """Fake acquisition image with analysis set."""

    def __init__(self) -> None:
        self.analysis_set = AcqAnalysisSet("fake.tif")


class FakeAcqImageList:
    """Fake image list resolving one file id."""

    def __init__(self, acq_image: FakeAcqImage) -> None:
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
        self.state = state


def test_controller_adds_event_from_x_range_and_publishes_state() -> None:
    """Controller should create event after plot range selection."""
    acq_image = FakeAcqImage()
    selection = PrimarySelection(file_id="file", channel=0, roi_id=1)
    home = FakeHomeController(FakeState(selection=selection, acq_image_list=FakeAcqImageList(acq_image)))
    bus = EventBus()
    begin_events: list[BeginPlotXRangeSelection] = []
    changed_events: list[AcqImageEventsChanged] = []
    selected_events: list[AcqImageEventSelectionChanged] = []
    bus.subscribe(BeginPlotXRangeSelection, lambda event: begin_events.append(event))
    bus.subscribe(AcqImageEventsChanged, lambda event: changed_events.append(event))
    bus.subscribe(AcqImageEventSelectionChanged, lambda event: selected_events.append(event))
    controller = EventAnalysisController(bus, home)  # type: ignore[arg-type]
    controller.bind()

    bus.publish(BeginAddAcqImageEventIntent(selection=selection))
    bus.publish(AcqImageEventXRangeSelectedIntent(selection=selection, x0=2.0, x1=5.0))

    assert begin_events
    analysis = acq_image.analysis_set.get_or_create(EventAnalysis.analysis_name, channel=0, roi_id=1)
    assert isinstance(analysis, EventAnalysis)
    assert len(analysis.get_rects()) == 1
    assert changed_events[-1].rows[0]["event_id"] == 1
    assert selected_events[-1].selected_event_id == 1


def test_controller_delete_selected_event() -> None:
    """Controller should delete selected event and clear selection."""
    acq_image = FakeAcqImage()
    analysis = acq_image.analysis_set.create(EventAnalysis.analysis_name, channel=0, roi_id=1)
    assert isinstance(analysis, EventAnalysis)
    analysis.add_rect(0.0, 1.0)
    selection = PrimarySelection(file_id="file", channel=0, roi_id=1)
    home = FakeHomeController(FakeState(selection=selection, acq_image_list=FakeAcqImageList(acq_image)))
    bus = EventBus()
    changed_events: list[AcqImageEventsChanged] = []
    bus.subscribe(AcqImageEventsChanged, lambda event: changed_events.append(event))
    controller = EventAnalysisController(bus, home, selected_event_id=1)  # type: ignore[arg-type]
    controller.bind()

    bus.publish(DeleteSelectedAcqImageEventIntent())

    assert analysis.get_rects() == []
    assert changed_events[-1].selected_event_id is None


def test_controller_visibility_publishes_state() -> None:
    """Controller should publish visibility changes."""
    acq_image = FakeAcqImage()
    selection = PrimarySelection(file_id="file", channel=0, roi_id=1)
    home = FakeHomeController(FakeState(selection=selection, acq_image_list=FakeAcqImageList(acq_image)))
    bus = EventBus()
    changed_events: list[AcqImageEventsChanged] = []
    bus.subscribe(AcqImageEventsChanged, lambda event: changed_events.append(event))
    controller = EventAnalysisController(bus, home)  # type: ignore[arg-type]
    controller.bind()

    bus.publish(SetAcqImageEventsVisibleIntent(visible=False))

    assert changed_events[-1].visible is False


def test_controller_refresh_request_publishes_current_rows() -> None:
    """Controller should publish existing event rows for a requested selection."""
    acq_image = FakeAcqImage()
    analysis = acq_image.analysis_set.create(EventAnalysis.analysis_name, channel=0, roi_id=1)
    assert isinstance(analysis, EventAnalysis)
    analysis.add_rect(2.0, 4.0)
    selection = PrimarySelection(file_id="file", channel=0, roi_id=1)
    home = FakeHomeController(FakeState(selection=selection, acq_image_list=FakeAcqImageList(acq_image)))
    bus = EventBus()
    changed_events: list[AcqImageEventsChanged] = []
    bus.subscribe(AcqImageEventsChanged, lambda event: changed_events.append(event))
    controller = EventAnalysisController(bus, home)  # type: ignore[arg-type]
    controller.bind()

    bus.publish(RequestAcqImageEventsRefreshIntent(selection=selection))

    assert changed_events[-1].rows[0]["event_id"] == 1
    assert changed_events[-1].rows[0]["x0"] == 2.0


def test_controller_selection_change_refreshes_rows_and_clears_selection() -> None:
    """Controller should refresh event rows when primary file selection changes."""
    acq_image = FakeAcqImage()
    analysis = acq_image.analysis_set.create(EventAnalysis.analysis_name, channel=0, roi_id=1)
    assert isinstance(analysis, EventAnalysis)
    analysis.add_rect(0.0, 1.0)
    selection = PrimarySelection(file_id="file", channel=0, roi_id=1)
    home = FakeHomeController(FakeState(selection=selection, acq_image_list=FakeAcqImageList(acq_image)))
    bus = EventBus()
    changed_events: list[AcqImageEventsChanged] = []
    selected_events: list[AcqImageEventSelectionChanged] = []
    bus.subscribe(AcqImageEventsChanged, lambda event: changed_events.append(event))
    bus.subscribe(AcqImageEventSelectionChanged, lambda event: selected_events.append(event))
    controller = EventAnalysisController(bus, home, selected_event_id=1)  # type: ignore[arg-type]
    controller.bind()

    bus.publish(FileSelectionChanged(file_id="file", acq_image=acq_image, channel=0, roi_id=1))

    assert selected_events[-1].selected_event_id is None
    assert changed_events[-1].rows[0]["event_id"] == 1
