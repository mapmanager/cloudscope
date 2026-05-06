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


def test_analysis_controller_cancel_intent_reaches_task_runner() -> None:
    """Controller should route analysis cancellation to TaskRunner."""
    from cloudscope.events import CancelTaskIntent

    bus = EventBus()
    task_runner = FakeTaskRunner()
    controller = AnalysisController(bus, FakeHomeController(), task_runner)  # type: ignore[arg-type]
    controller.bind()

    bus.publish(CancelTaskIntent(task_kind=TaskKind.ANALYSIS))

    assert task_runner.cancelled
