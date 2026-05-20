"""Tests for AnalysisController."""

from dataclasses import dataclass

from cloudscope.controllers.analysis_controller import AnalysisController
from cloudscope.event_bus import EventBus
from cloudscope.events import AnalysisKind, AppStatusChanged, RunAnalysisIntent, TaskKind
from cloudscope.state import PrimarySelection


@dataclass
class FakeState:
    """Fake home-controller state."""

    acq_image_list: object | None = None


class FakeHomeController:
    """Fake home page controller."""

    def __init__(self) -> None:
        self.state = FakeState()


class FakeTaskRunner:
    """Fake task runner recording starts and cancels."""

    def __init__(self) -> None:
        self.started = False
        self.cancelled = False

    def start(self, **_kwargs) -> str:
        """Record task start."""
        self.started = True
        return "task-id"

    def cancel(self, *, task_kind, task_id=None) -> bool:
        """Record cancellation."""
        self.cancelled = task_kind is TaskKind.ANALYSIS and task_id is None
        return self.cancelled


def test_analysis_controller_rejects_missing_selection() -> None:
    """Controller should publish status instead of starting invalid analysis."""
    bus = EventBus()
    statuses = []
    bus.subscribe(AppStatusChanged, lambda event: statuses.append(event))
    task_runner = FakeTaskRunner()
    controller = AnalysisController(bus, FakeHomeController(), task_runner)  # type: ignore[arg-type]
    controller.bind()

    bus.publish(
        RunAnalysisIntent(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(),
            detection_params={},
        )
    )

    assert not task_runner.started
    assert statuses


def test_analysis_controller_rejects_exclusive_conflict() -> None:
    """Controller should refuse Diameter while Radon exists for same ROI."""
    import numpy as np

    from acqstore.acq_image.acq_analysis_set import AcqAnalysisSet

    class FakeProvider:
        def get_roi_image(self, channel: int, roi_id: int) -> np.ndarray:
            _ = channel, roi_id
            image = np.zeros((48, 64), dtype=np.float32)
            image[:, 20:40] = 180.0
            return image

        def get_image_physical_units(self) -> tuple[float, float]:
            return (0.001, 0.25)

    class FakeAcqImage:
        def __init__(self) -> None:
            self.analysis_set = AcqAnalysisSet("fake.tif", data_provider=FakeProvider())

    class FakeAcqImageList:
        def __init__(self, acq_image: FakeAcqImage) -> None:
            self._image = acq_image

        def get_file_by_id(self, file_id: str) -> FakeAcqImage:
            _ = file_id
            return self._image

    acq_image = FakeAcqImage()
    acq_image.analysis_set.create("radon_velocity", channel=0, roi_id=1)

    bus = EventBus()
    statuses: list[AppStatusChanged] = []
    bus.subscribe(AppStatusChanged, lambda event: statuses.append(event))
    task_runner = FakeTaskRunner()
    home_controller = FakeHomeController()
    home_controller.state.acq_image_list = FakeAcqImageList(acq_image)
    controller = AnalysisController(bus, home_controller, task_runner)  # type: ignore[arg-type]
    controller.bind()

    bus.publish(
        RunAnalysisIntent(
            analysis_kind=AnalysisKind.DIAMETER,
            selection=PrimarySelection(file_id="file", channel=0, roi_id=1),
            detection_params={},
        )
    )

    assert not task_runner.started
    assert statuses
    assert "primary_kymograph" in statuses[0].message or "already" in statuses[0].message.lower()


def test_analysis_controller_cancel_intent_reaches_task_runner() -> None:
    """Controller should route analysis cancellation to TaskRunner."""
    from cloudscope.events import CancelTaskIntent

    bus = EventBus()
    task_runner = FakeTaskRunner()
    controller = AnalysisController(bus, FakeHomeController(), task_runner)  # type: ignore[arg-type]
    controller.bind()

    bus.publish(CancelTaskIntent(task_kind=TaskKind.ANALYSIS))

    assert task_runner.cancelled
