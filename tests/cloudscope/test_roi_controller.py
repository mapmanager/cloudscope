"""Tests for CloudScope RoiController."""

from dataclasses import dataclass

from cloudscope.controllers.roi_controller import RoiController
from cloudscope.event_bus import EventBus
from cloudscope.events.roi import (
    AddRoiIntent,
    ApplyRoiFullHeightIntent,
    ApplyRoiFullWidthIntent,
    BeginEditRoiIntent,
    CancelEditRoiIntent,
    DeleteRoiIntent,
    RoiChanged,
    RoiChangeKind,
    RoiEditModeChanged,
    SubmitEditRoiIntent,
)
from cloudscope.events.status import StatusLevel
from cloudscope.state import PrimarySelection


@dataclass(frozen=True)
class FakeKey:
    """Fake analysis key."""

    analysis_name: str
    channel: int
    roi_id: int


@dataclass(frozen=True)
class FakeAnalysis:
    """Fake analysis instance."""

    key: FakeKey


@dataclass
class FakeRoi:
    """Fake ROI."""

    roi_id: int


class FakeRoiSet:
    """Fake ROI set implementing the controller API."""

    def __init__(self, roi_ids: list[int] | None = None) -> None:
        self.roi_ids = list(roi_ids or [])
        self.next_id = max(self.roi_ids, default=0) + 1

    def create_rect_roi(self) -> FakeRoi:
        """Create a fake ROI."""
        roi = FakeRoi(self.next_id)
        self.roi_ids.append(roi.roi_id)
        self.next_id += 1
        return roi

    def has_roi(self, roi_id: int) -> bool:
        """Return whether ROI exists."""
        return roi_id in self.roi_ids

    def get_roi_ids(self) -> list[int]:
        """Return ROI ids."""
        return list(self.roi_ids)

    def delete(self, roi_id: int) -> None:
        """Delete ROI."""
        self.roi_ids.remove(roi_id)


class FakeAnalysisSet:
    """Fake analysis set with ROI dependency APIs."""

    def __init__(self, analyses: list[FakeAnalysis] | None = None) -> None:
        self.analyses = list(analyses or [])
        self.deleted_roi_ids: list[int] = []

    def as_list(self) -> list[FakeAnalysis]:
        """Return analyses."""
        return list(self.analyses)

    def delete_roi(self, roi_id: int) -> int:
        """Delete analyses for ROI."""
        removed = [analysis for analysis in self.analyses if analysis.key.roi_id == roi_id]
        self.analyses = [analysis for analysis in self.analyses if analysis.key.roi_id != roi_id]
        self.deleted_roi_ids.append(roi_id)
        return len(removed)


class FakeAcqImage:
    """Fake AcqImage."""

    def __init__(self) -> None:
        self.file_id = "file-a"
        self.rois = FakeRoiSet([1, 2])
        self.analysis_set = FakeAnalysisSet()


class FakeAcqImageList:
    """Fake AcqImageList."""

    def __init__(self, image: FakeAcqImage) -> None:
        self.image = image

    def get_file_by_id(self, file_id: str) -> FakeAcqImage | None:
        """Return image by id."""
        if file_id == self.image.file_id:
            return self.image
        return None


@dataclass
class FakeState:
    """Fake page state."""

    acq_image_list: FakeAcqImageList
    selection: PrimarySelection


class FakeHomeController:
    """Fake home controller exposing state and select_roi."""

    def __init__(self, image: FakeAcqImage) -> None:
        self.state = FakeState(
            acq_image_list=FakeAcqImageList(image),
            selection=PrimarySelection(file_id=image.file_id, channel=0, roi_id=1),
        )
        self.selected_roi_ids: list[int | None] = []

    def select_roi(self, roi_id: int | None) -> None:
        """Record ROI selection."""
        self.state.selection.roi_id = roi_id
        self.selected_roi_ids.append(roi_id)


class FakeDialog:
    """Fake dialog invoking no UI by default."""

    instances: list["FakeDialog"] = []

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.opened = False
        FakeDialog.instances.append(self)

    def open(self) -> None:
        """Record open."""
        self.opened = True


def test_roi_controller_add_creates_roi_selects_it_and_publishes_changed() -> None:
    """AddRoiIntent should create a new full-image ROI and select it."""
    bus = EventBus()
    image = FakeAcqImage()
    home = FakeHomeController(image)
    events: list[RoiChanged] = []
    bus.subscribe(RoiChanged, events.append)
    controller = RoiController(bus, home)  # type: ignore[arg-type]
    controller.bind()

    bus.publish(AddRoiIntent(selection=PrimarySelection(file_id="file-a", channel=0, roi_id=None)))

    assert image.rois.get_roi_ids() == [1, 2, 3]
    assert home.selected_roi_ids == [3]
    assert events[-1].operation is RoiChangeKind.ADD
    assert events[-1].selection.roi_id == 3


def test_roi_controller_delete_without_analysis_deletes_immediately() -> None:
    """DeleteRoiIntent without dependencies should delete without confirmation dialog."""
    bus = EventBus()
    image = FakeAcqImage()
    home = FakeHomeController(image)
    events: list[RoiChanged] = []
    bus.subscribe(RoiChanged, events.append)
    controller = RoiController(bus, home, dialog_factory=FakeDialog)  # type: ignore[arg-type]
    controller.bind()

    bus.publish(DeleteRoiIntent(selection=PrimarySelection(file_id="file-a", channel=0, roi_id=2)))

    assert image.rois.get_roi_ids() == [1]
    assert image.analysis_set.deleted_roi_ids == [2]
    assert home.selected_roi_ids == [1]
    assert events[-1].operation is RoiChangeKind.DELETE
    assert events[-1].removed_analysis_count == 0


def test_roi_controller_delete_with_analysis_waits_for_confirmation() -> None:
    """Delete with dependencies should open dialog and delete only on yes callback."""
    FakeDialog.instances.clear()
    bus = EventBus()
    image = FakeAcqImage()
    image.analysis_set = FakeAnalysisSet([FakeAnalysis(FakeKey("radon_velocity", 0, 2))])
    home = FakeHomeController(image)
    events: list[RoiChanged] = []
    bus.subscribe(RoiChanged, events.append)
    controller = RoiController(bus, home, dialog_factory=FakeDialog)  # type: ignore[arg-type]
    controller.bind()

    bus.publish(DeleteRoiIntent(selection=PrimarySelection(file_id="file-a", channel=0, roi_id=2)))

    assert image.rois.get_roi_ids() == [1, 2]
    assert FakeDialog.instances and FakeDialog.instances[-1].opened
    assert "radon_velocity" in FakeDialog.instances[-1].kwargs["message"]

    FakeDialog.instances[-1].kwargs["on_yes"]()

    assert image.rois.get_roi_ids() == [1]
    assert image.analysis_set.deleted_roi_ids == [2]
    assert events[-1].removed_analysis_count == 1


def test_roi_controller_begin_edit_publishes_edit_mode() -> None:
    """BeginEditRoiIntent should publish edit-mode state for an existing ROI."""
    bus = EventBus()
    image = FakeAcqImage()
    home = FakeHomeController(image)
    events: list[RoiEditModeChanged] = []
    bus.subscribe(RoiEditModeChanged, events.append)
    controller = RoiController(bus, home)  # type: ignore[arg-type]
    controller.bind()

    selection = PrimarySelection(file_id="file-a", channel=0, roi_id=1)
    bus.publish(BeginEditRoiIntent(selection=selection))

    assert events == [RoiEditModeChanged(is_editing=True, selection=selection, message="Editing ROI 1.")]


def test_roi_controller_cancel_edit_publishes_idle_edit_mode() -> None:
    """CancelEditRoiIntent should publish idle edit-mode state."""
    bus = EventBus()
    image = FakeAcqImage()
    home = FakeHomeController(image)
    events: list[RoiEditModeChanged] = []
    bus.subscribe(RoiEditModeChanged, events.append)
    controller = RoiController(bus, home)  # type: ignore[arg-type]
    controller.bind()

    bus.publish(CancelEditRoiIntent(selection=PrimarySelection(file_id="file-a", channel=0, roi_id=1)))

    assert events == [
        RoiEditModeChanged(is_editing=False, selection=None, message="ROI edit cancelled.")
    ]


def test_roi_controller_submit_edit_exits_mode_and_warns() -> None:
    """SubmitEditRoiIntent should exit edit mode until geometry editing exists."""
    bus = EventBus()
    image = FakeAcqImage()
    home = FakeHomeController(image)
    mode_events: list[RoiEditModeChanged] = []
    status_events = []
    bus.subscribe(RoiEditModeChanged, mode_events.append)
    from cloudscope.events.status import AppStatusChanged
    bus.subscribe(AppStatusChanged, status_events.append)
    controller = RoiController(bus, home)  # type: ignore[arg-type]
    controller.bind()

    bus.publish(SubmitEditRoiIntent(selection=PrimarySelection(file_id="file-a", channel=0, roi_id=1)))

    assert mode_events == [
        RoiEditModeChanged(
            is_editing=False,
            selection=None,
            message="ROI edit submitted; geometry editing is not implemented yet.",
        )
    ]
    assert status_events[-1].level is StatusLevel.WARNING


def test_roi_controller_full_extent_edit_intents_warn_only() -> None:
    """Full-width/full-height edit intents are placeholders in ROI-2."""
    bus = EventBus()
    image = FakeAcqImage()
    home = FakeHomeController(image)
    from cloudscope.events.status import AppStatusChanged
    status_events: list[AppStatusChanged] = []
    bus.subscribe(AppStatusChanged, status_events.append)
    controller = RoiController(bus, home)  # type: ignore[arg-type]
    controller.bind()

    selection = PrimarySelection(file_id="file-a", channel=0, roi_id=1)
    bus.publish(ApplyRoiFullWidthIntent(selection=selection))
    bus.publish(ApplyRoiFullHeightIntent(selection=selection))

    assert [event.level for event in status_events[-2:]] == [StatusLevel.WARNING, StatusLevel.WARNING]
