"""Tests for CloudScope RoiController."""

from dataclasses import dataclass

from acqstore.acq_image.roi import ImageBounds, RectROI, RectRoiBounds
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
    RoiEditPreviewChanged,
    SubmitEditRoiIntent,
)
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


class FakeRoiSet:
    """Fake ROI set implementing the controller API."""

    def __init__(self, roi_ids: list[int] | None = None) -> None:
        self.image_bounds = ImageBounds(width=100, height=50)
        self.rois = {
            roi_id: RectROI(
                roi_id=roi_id,
                bounds=RectRoiBounds(
                    dim0_start=roi_id,
                    dim0_stop=roi_id + 10,
                    dim1_start=roi_id,
                    dim1_stop=roi_id + 20,
                ),
            )
            for roi_id in list(roi_ids or [])
        }
        self.next_id = max(self.rois, default=0) + 1

    def create_rect_roi(self) -> RectROI:
        """Create a fake ROI."""
        roi = RectROI(
            roi_id=self.next_id,
            bounds=RectRoiBounds.from_image_bounds(self.image_bounds),
        )
        self.rois[roi.roi_id] = roi
        self.next_id += 1
        return roi

    def has_roi(self, roi_id: int) -> bool:
        """Return whether ROI exists."""
        return roi_id in self.rois

    def get_roi_ids(self) -> list[int]:
        """Return ROI ids."""
        return list(self.rois)

    def get(self, roi_id: int) -> RectROI | None:
        """Return ROI by id."""
        return self.rois.get(roi_id)

    def edit_rect_roi(self, roi_id: int, *, bounds: RectRoiBounds) -> RectROI:
        """Edit fake rectangular ROI bounds."""
        roi = self.rois[roi_id]
        roi.bounds = bounds.clamped_to(self.image_bounds)
        return roi

    def delete(self, roi_id: int) -> None:
        """Delete ROI."""
        del self.rois[roi_id]


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


def test_roi_controller_submit_edit_commits_pending_bounds() -> None:
    """SubmitEditRoiIntent should commit the latest staged bounds."""
    bus = EventBus()
    image = FakeAcqImage()
    home = FakeHomeController(image)
    mode_events: list[RoiEditModeChanged] = []
    changed_events: list[RoiChanged] = []
    bus.subscribe(RoiEditModeChanged, mode_events.append)
    bus.subscribe(RoiChanged, changed_events.append)
    controller = RoiController(bus, home)  # type: ignore[arg-type]
    controller.bind()

    selection = PrimarySelection(file_id="file-a", channel=0, roi_id=1)
    bounds = RectRoiBounds(dim0_start=3, dim0_stop=12, dim1_start=4, dim1_stop=18)
    bus.publish(BeginEditRoiIntent(selection=selection))
    bus.publish(RoiEditPreviewChanged(selection=selection, bounds=bounds))
    bus.publish(SubmitEditRoiIntent(selection=selection))

    assert image.rois.get(1).bounds == bounds
    assert home.selected_roi_ids == [1]
    assert changed_events[-1] == RoiChanged(
        operation=RoiChangeKind.EDIT,
        selection=selection,
        removed_analysis_count=0,
    )
    assert mode_events[-1] == RoiEditModeChanged(
        is_editing=False,
        selection=None,
        message="ROI 1 edit submitted.",
    )


def test_roi_controller_submit_edit_with_analysis_waits_for_confirmation() -> None:
    """Submitting edited ROI with dependencies should wait for dialog confirmation."""
    FakeDialog.instances.clear()
    bus = EventBus()
    image = FakeAcqImage()
    image.analysis_set = FakeAnalysisSet([FakeAnalysis(FakeKey("diameter", 0, 1))])
    home = FakeHomeController(image)
    changed_events: list[RoiChanged] = []
    bus.subscribe(RoiChanged, changed_events.append)
    controller = RoiController(bus, home, dialog_factory=FakeDialog)  # type: ignore[arg-type]
    controller.bind()

    selection = PrimarySelection(file_id="file-a", channel=0, roi_id=1)
    bounds = RectRoiBounds(dim0_start=5, dim0_stop=15, dim1_start=6, dim1_stop=16)
    bus.publish(BeginEditRoiIntent(selection=selection))
    bus.publish(RoiEditPreviewChanged(selection=selection, bounds=bounds))
    bus.publish(SubmitEditRoiIntent(selection=selection))

    assert image.rois.get(1).bounds != bounds
    assert FakeDialog.instances and FakeDialog.instances[-1].opened
    assert "diameter" in FakeDialog.instances[-1].kwargs["message"]

    FakeDialog.instances[-1].kwargs["on_yes"]()

    assert image.rois.get(1).bounds == bounds
    assert image.analysis_set.deleted_roi_ids == [1]
    assert changed_events[-1].removed_analysis_count == 1


def test_roi_controller_full_extent_edit_intents_publish_previews() -> None:
    """Full-width/full-height edit intents should stage preview bounds only."""
    bus = EventBus()
    image = FakeAcqImage()
    home = FakeHomeController(image)
    preview_events: list[RoiEditPreviewChanged] = []
    bus.subscribe(RoiEditPreviewChanged, preview_events.append)
    controller = RoiController(bus, home)  # type: ignore[arg-type]
    controller.bind()

    selection = PrimarySelection(file_id="file-a", channel=0, roi_id=1)
    bus.publish(BeginEditRoiIntent(selection=selection))
    bus.publish(ApplyRoiFullWidthIntent(selection=selection))
    bus.publish(ApplyRoiFullHeightIntent(selection=selection))

    assert preview_events[-2].bounds == RectRoiBounds(
        dim0_start=0,
        dim0_stop=50,
        dim1_start=1,
        dim1_stop=21,
    )
    assert preview_events[-1].bounds == RectRoiBounds(
        dim0_start=0,
        dim0_stop=50,
        dim1_start=0,
        dim1_stop=100,
    )
