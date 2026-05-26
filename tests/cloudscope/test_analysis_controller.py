"""Tests for AnalysisController."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cloudscope.controllers.analysis_controller import AnalysisController
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import (
    AnalysisCompleted,
    AnalysisKind,
    CancelTaskIntent,
    RunAnalysisIntent,
    TaskKind,
)
from cloudscope.events.status import AppStatusChanged, StatusLevel
from cloudscope.state import PrimarySelection


@dataclass
class FakeState:
    """Fake home-controller state."""

    acq_image_list: object | None = None


class FakeHomeController:
    """Fake home page controller."""

    def __init__(self) -> None:
        self.state = FakeState()


@dataclass
class CapturedTaskStart:
    """Captured arguments from a TaskRunner.start call."""

    task_kind: TaskKind
    task_label: str
    worker: Any
    on_completed: Any
    on_failed: Any
    on_cancelled: Any


class FakeTaskRunner:
    """Fake task runner recording starts, cancels, and exposing callbacks."""

    def __init__(self) -> None:
        self.started = False
        self.cancelled = False
        self.captured: CapturedTaskStart | None = None
        self.cancel_result = True

    def start(
        self,
        *,
        task_kind: TaskKind,
        task_label: str,
        worker: Any,
        on_completed: Any = None,
        on_failed: Any = None,
        on_cancelled: Any = None,
    ) -> str:
        """Capture start args for inspection."""
        self.started = True
        self.captured = CapturedTaskStart(
            task_kind=task_kind,
            task_label=task_label,
            worker=worker,
            on_completed=on_completed,
            on_failed=on_failed,
            on_cancelled=on_cancelled,
        )
        return "task-id"

    def cancel(self, *, task_kind, task_id=None) -> bool:
        """Record cancellation."""
        self.cancelled = task_kind is TaskKind.ANALYSIS and task_id is None
        return self.cancel_result


@dataclass
class RecordedProgress:
    """Captured progress callback arguments."""

    fraction: float | None
    message: str


class FakeTaskContext:
    """Stand-in for TaskContext used by worker test calls."""

    def __init__(self, *, cancelled: bool = False) -> None:
        self.progress: list[RecordedProgress] = []
        self._cancelled = cancelled
        self.raise_called = 0

    def report_progress(self, fraction: float | None, message: str = "") -> None:
        self.progress.append(RecordedProgress(fraction=fraction, message=message))

    def is_cancelled(self) -> bool:
        return self._cancelled

    def raise_if_cancelled(self) -> None:
        self.raise_called += 1
        if self._cancelled:
            from cloudscope.task_runner import TaskCancelled

            raise TaskCancelled("cancelled")


# ---- shared fakes for worker tests ----


@dataclass
class FakeAnalysis:
    """Minimal stand-in for BaseAnalysis."""

    key: Any
    detection_params: dict[str, Any] = field(default_factory=dict)

    def set_detection_params(self, params: dict[str, Any]) -> None:
        self.detection_params = dict(params)


class FakeAnalysisSet:
    """Stand-in for AcqAnalysisSet exposing the methods the worker calls."""

    def __init__(self) -> None:
        self._items: dict[Any, FakeAnalysis] = {}
        self.created: list[tuple[str, int, int, dict[str, Any]]] = []
        self.removed: list[Any] = []
        self.runs: list[Any] = []
        self.primary: dict[tuple[int, int], FakeAnalysis] = {}

    def get(self, key):
        return self._items.get(key)

    def remove(self, key) -> None:
        self.removed.append(key)
        self._items.pop(key, None)

    def create(
        self,
        analysis_name: str,
        *,
        channel: int,
        roi_id: int,
        detection_params: dict[str, Any] | None = None,
    ) -> Any:
        from acqstore.acq_image.analysis.model import AnalysisKey

        params = dict(detection_params or {})
        self.created.append((analysis_name, channel, roi_id, params))
        if analysis_name == "radon_velocity":
            from acqstore.acq_image.analysis.velocity_analysis.radon_velocity_analysis import (
                RadonVelocityAnalysis,
            )

            analysis: Any = RadonVelocityAnalysis(channel=channel, roi_id=roi_id)
        elif analysis_name == "diameter":
            from acqstore.acq_image.analysis.diameter_analysis.diameter_analysis import (
                DiameterAnalysis,
            )

            analysis = DiameterAnalysis(channel=channel, roi_id=roi_id)
        elif analysis_name == "event":
            from acqstore.acq_image.analysis.event_analysis.event_analysis import EventAnalysis

            analysis = EventAnalysis(channel=channel, roi_id=roi_id)
        else:
            key = AnalysisKey(analysis_name, channel, roi_id)
            analysis = FakeAnalysis(key=key, detection_params=params)
        self._items[analysis.key] = analysis
        return analysis

    def run_analysis(self, key, *, context) -> None:
        self.runs.append((key, context))

    def get_primary_kymograph_analysis(self, *, channel: int, roi_id: int):
        return self.primary.get((channel, roi_id))


class FakeAcqImage:
    def __init__(self, analysis_set: FakeAnalysisSet | None = None) -> None:
        self.analysis_set = analysis_set or FakeAnalysisSet()


class FakeAcqImageList:
    def __init__(self, acq_image: FakeAcqImage | None) -> None:
        self._image = acq_image

    def get_file_by_id(self, file_id: str):
        _ = file_id
        return self._image


def _make_controller() -> tuple[AnalysisController, EventBus, FakeTaskRunner, FakeHomeController, list[AppStatusChanged], list[AnalysisCompleted]]:
    bus = EventBus()
    statuses: list[AppStatusChanged] = []
    completed: list[AnalysisCompleted] = []
    bus.subscribe(AppStatusChanged, statuses.append)
    bus.subscribe(AnalysisCompleted, completed.append)
    home = FakeHomeController()
    runner = FakeTaskRunner()
    controller = AnalysisController(bus, home, runner)  # type: ignore[arg-type]
    controller.bind()
    return controller, bus, runner, home, statuses, completed


# ---- validation / dispatch tests ----


def test_analysis_controller_rejects_missing_selection() -> None:
    """Controller should publish status instead of starting invalid analysis."""
    bus = EventBus()
    statuses: list[AppStatusChanged] = []
    bus.subscribe(AppStatusChanged, statuses.append)
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

    class _Provider:
        def get_roi_image(self, channel: int, roi_id: int) -> np.ndarray:
            _ = channel, roi_id
            image = np.zeros((48, 64), dtype=np.float32)
            image[:, 20:40] = 180.0
            return image

        def get_image_physical_units(self) -> tuple[float, float]:
            return (0.001, 0.25)

    class _Image:
        def __init__(self) -> None:
            self.analysis_set = AcqAnalysisSet("fake.tif", data_provider=_Provider())

    class _List:
        def __init__(self, acq_image: _Image) -> None:
            self._image = acq_image

        def get_file_by_id(self, file_id: str) -> _Image:
            _ = file_id
            return self._image

    acq_image = _Image()
    acq_image.analysis_set.create("radon_velocity", channel=0, roi_id=1)

    bus = EventBus()
    statuses: list[AppStatusChanged] = []
    bus.subscribe(AppStatusChanged, statuses.append)
    task_runner = FakeTaskRunner()
    home_controller = FakeHomeController()
    home_controller.state.acq_image_list = _List(acq_image)
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
    bus = EventBus()
    task_runner = FakeTaskRunner()
    controller = AnalysisController(bus, FakeHomeController(), task_runner)  # type: ignore[arg-type]
    controller.bind()

    bus.publish(CancelTaskIntent(task_kind=TaskKind.ANALYSIS))

    assert task_runner.cancelled


def test_analysis_controller_ignores_non_analysis_cancel() -> None:
    """Cancel intents for other task kinds should not touch the runner."""
    _, bus, runner, _, _, _ = _make_controller()

    bus.publish(CancelTaskIntent(task_kind=TaskKind.SAVE))

    assert runner.cancelled is False


def test_analysis_controller_cancel_publishes_warning_when_nothing_running() -> None:
    """Cancel should publish a warning when the runner reports nothing to cancel."""
    _, bus, runner, _, statuses, _ = _make_controller()
    runner.cancel_result = False

    bus.publish(CancelTaskIntent(task_kind=TaskKind.ANALYSIS))

    assert statuses
    assert statuses[-1].level is StatusLevel.WARNING
    assert "No running analysis" in statuses[-1].message


def test_analysis_controller_rejects_no_acq_image_list() -> None:
    """Selection valid but no AcqImageList loaded should fail-fast with status."""
    _, bus, runner, _, statuses, _ = _make_controller()

    bus.publish(
        RunAnalysisIntent(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            detection_params={},
        )
    )

    assert not runner.started
    assert statuses
    assert "Analysis could not start" in statuses[-1].message


def test_analysis_controller_rejects_missing_channel_and_roi() -> None:
    """Each missing required selection field should be reported."""
    _, bus, runner, _, statuses, _ = _make_controller()

    bus.publish(
        RunAnalysisIntent(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="f", channel=None, roi_id=1),
            detection_params={},
        )
    )
    bus.publish(
        RunAnalysisIntent(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=None),
            detection_params={},
        )
    )

    assert not runner.started
    assert len(statuses) == 2
    assert "channel" in statuses[0].message.lower()
    assert "roi" in statuses[1].message.lower()


# ---- _on_run_analysis happy path -> TaskRunner.start ----


def test_analysis_controller_starts_task_with_expected_label_and_kind() -> None:
    """A valid intent should start a TaskKind.ANALYSIS task labelled with the kind."""
    controller, bus, runner, home, _, _ = _make_controller()
    home.state.acq_image_list = FakeAcqImageList(FakeAcqImage())

    bus.publish(
        RunAnalysisIntent(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            detection_params={},
        )
    )

    assert runner.started
    assert runner.captured is not None
    assert runner.captured.task_kind is TaskKind.ANALYSIS
    assert "radon_velocity" in runner.captured.task_label
    assert callable(runner.captured.worker)
    assert callable(runner.captured.on_completed)
    assert callable(runner.captured.on_failed)
    assert callable(runner.captured.on_cancelled)


# ---- _run_analysis_worker tests ----


def test_worker_creates_analysis_and_runs_for_event_kind() -> None:
    """EVENT kind without existing analysis should create then run."""
    controller, bus, runner, home, _, _ = _make_controller()
    aset = FakeAnalysisSet()
    home.state.acq_image_list = FakeAcqImageList(FakeAcqImage(aset))

    bus.publish(
        RunAnalysisIntent(
            analysis_kind=AnalysisKind.EVENT,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            detection_params={"min_height": 0.5},
        )
    )
    ctx = FakeTaskContext()
    runner.captured.worker(ctx)

    assert aset.created == [("event", 0, 1, {"min_height": 0.5})]
    assert aset.removed == []
    assert len(aset.runs) == 1
    assert ctx.progress[0].fraction == 0.0
    assert ctx.progress[-1].fraction == 1.0
    assert ctx.raise_called == 1


def test_worker_updates_detection_params_when_existing_event_analysis() -> None:
    """An existing EventAnalysis should have its detection params updated, not be recreated."""
    from acqstore.acq_image.analysis.event_analysis.event_analysis import EventAnalysis

    controller, bus, runner, home, _, _ = _make_controller()
    aset = FakeAnalysisSet()
    existing = EventAnalysis(channel=0, roi_id=1)
    aset._items[existing.key] = existing  # type: ignore[assignment]
    home.state.acq_image_list = FakeAcqImageList(FakeAcqImage(aset))

    bus.publish(
        RunAnalysisIntent(
            analysis_kind=AnalysisKind.EVENT,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            detection_params={"pre_post_win_sec": 0.5},
        )
    )
    runner.captured.worker(FakeTaskContext())

    assert aset.created == []
    assert existing.detection_params["pre_post_win_sec"] == 0.5


def test_worker_removes_then_creates_for_non_event_kind() -> None:
    """Non-event kinds should remove any prior analysis for the key before creating."""
    controller, bus, runner, home, _, _ = _make_controller()
    aset = FakeAnalysisSet()
    home.state.acq_image_list = FakeAcqImageList(FakeAcqImage(aset))

    bus.publish(
        RunAnalysisIntent(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="f", channel=2, roi_id=3),
            detection_params={"theta_min": -45},
        )
    )
    runner.captured.worker(FakeTaskContext())

    assert aset.removed and aset.removed[0].analysis_name == "radon_velocity"
    assert aset.created and aset.created[0][:3] == ("radon_velocity", 2, 3)


def test_worker_raises_when_acq_image_no_longer_loaded() -> None:
    """Worker should raise RuntimeError if the snapshot file_id was unloaded."""
    import pytest

    controller, bus, runner, home, _, _ = _make_controller()
    home.state.acq_image_list = FakeAcqImageList(None)

    bus.publish(
        RunAnalysisIntent(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            detection_params={},
        )
    )
    with pytest.raises(RuntimeError, match="no longer loaded"):
        runner.captured.worker(FakeTaskContext())


def test_worker_raises_when_acq_image_list_disappears_between_validate_and_worker() -> None:
    """Worker should raise RuntimeError if AcqImageList vanished before worker ran."""
    import pytest

    controller, bus, runner, home, _, _ = _make_controller()
    home.state.acq_image_list = FakeAcqImageList(FakeAcqImage())
    bus.publish(
        RunAnalysisIntent(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            detection_params={},
        )
    )

    home.state.acq_image_list = None
    with pytest.raises(RuntimeError, match="No AcqImageList loaded"):
        runner.captured.worker(FakeTaskContext())


def test_worker_reruns_dependent_event_analysis_after_radon() -> None:
    """When a downstream EventAnalysis exists, the worker should rerun it."""
    from acqstore.acq_image.analysis.event_analysis.event_analysis import EventAnalysis

    controller, bus, runner, home, _, _ = _make_controller()
    aset = FakeAnalysisSet()
    existing_event = EventAnalysis(channel=0, roi_id=1)
    aset._items[existing_event.key] = existing_event  # type: ignore[assignment]
    home.state.acq_image_list = FakeAcqImageList(FakeAcqImage(aset))

    bus.publish(
        RunAnalysisIntent(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            detection_params={},
        )
    )
    runner.captured.worker(FakeTaskContext())

    radon_key_runs = [k for k, _ in aset.runs if k.analysis_name == "radon_velocity"]
    event_key_runs = [k for k, _ in aset.runs if k.analysis_name == "event"]
    assert len(radon_key_runs) == 1
    assert len(event_key_runs) == 1


def test_worker_skips_dependent_event_when_absent() -> None:
    """Worker should not run a non-existent dependent event analysis."""
    controller, bus, runner, home, _, _ = _make_controller()
    aset = FakeAnalysisSet()
    home.state.acq_image_list = FakeAcqImageList(FakeAcqImage(aset))

    bus.publish(
        RunAnalysisIntent(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            detection_params={},
        )
    )
    runner.captured.worker(FakeTaskContext())

    assert [k.analysis_name for k, _ in aset.runs] == ["radon_velocity"]


def test_worker_cancel_raises_before_running() -> None:
    """A cancelled context should abort before run_analysis is called."""
    import pytest

    from cloudscope.task_runner import TaskCancelled

    controller, bus, runner, home, _, _ = _make_controller()
    aset = FakeAnalysisSet()
    home.state.acq_image_list = FakeAcqImageList(FakeAcqImage(aset))

    bus.publish(
        RunAnalysisIntent(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            detection_params={},
        )
    )
    with pytest.raises(TaskCancelled):
        runner.captured.worker(FakeTaskContext(cancelled=True))
    assert aset.runs == []


# ---- callback publishing ----


def test_completed_callback_publishes_success_events() -> None:
    """on_completed should publish AnalysisCompleted(success=True) + INFO status."""
    controller, bus, runner, home, statuses, completed = _make_controller()
    home.state.acq_image_list = FakeAcqImageList(FakeAcqImage())
    bus.publish(
        RunAnalysisIntent(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            detection_params={},
        )
    )
    statuses.clear()
    completed.clear()

    runner.captured.on_completed(None)

    assert len(completed) == 1
    assert completed[0].success is True
    assert completed[0].selection.file_id == "f"
    assert statuses[-1].level is StatusLevel.INFO


def test_failed_callback_publishes_failure_events() -> None:
    """on_failed should publish AnalysisCompleted(success=False) + WARNING status."""
    controller, bus, runner, home, statuses, completed = _make_controller()
    home.state.acq_image_list = FakeAcqImageList(FakeAcqImage())
    bus.publish(
        RunAnalysisIntent(
            analysis_kind=AnalysisKind.DIAMETER,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            detection_params={},
        )
    )
    statuses.clear()
    completed.clear()

    runner.captured.on_failed(RuntimeError("boom"))

    assert len(completed) == 1
    assert completed[0].success is False
    assert "boom" in completed[0].message
    assert statuses[-1].level is StatusLevel.WARNING


def test_cancelled_callback_publishes_cancelled_events() -> None:
    """on_cancelled should publish AnalysisCompleted(success=False) with cancel message."""
    controller, bus, runner, home, statuses, completed = _make_controller()
    home.state.acq_image_list = FakeAcqImageList(FakeAcqImage())
    bus.publish(
        RunAnalysisIntent(
            analysis_kind=AnalysisKind.EVENT,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            detection_params={},
        )
    )
    statuses.clear()
    completed.clear()

    runner.captured.on_cancelled()

    assert len(completed) == 1
    assert completed[0].success is False
    assert "cancel" in completed[0].message.lower()


def test_copy_selection_returns_independent_instance() -> None:
    """_copy_selection should return a structurally equal but distinct selection."""
    original = PrimarySelection(file_id="x", channel=2, roi_id=5)
    copy = AnalysisController._copy_selection(original)

    assert copy == original
    assert copy is not original
