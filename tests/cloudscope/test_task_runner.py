"""Tests for CloudScope TaskRunner."""

from cloudscope.event_bus import EventBus
from cloudscope.events import AppBusyChanged, TaskKind, TaskProgressChanged, TaskStatus
from cloudscope.task_runner import TaskRunner, TaskRunnerMessage, TaskRunnerMessageKind


class FakeTimer:
    """Fake NiceGUI timer used by tests."""

    def __init__(self) -> None:
        self.cancelled = False

    def cancel(self) -> None:
        """Mark timer cancelled."""
        self.cancelled = True


def test_task_runner_rejects_second_active_task(monkeypatch) -> None:
    """TaskRunner should allow only one active task."""
    monkeypatch.setattr("cloudscope.task_runner.ui.timer", lambda *_args, **_kwargs: FakeTimer())
    bus = EventBus()
    runner = TaskRunner(bus)

    runner.start(task_kind=TaskKind.ANALYSIS, task_label="Analysis", worker=lambda _ctx: None)

    try:
        runner.start(task_kind=TaskKind.SAVE, task_label="Save", worker=lambda _ctx: None)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected RuntimeError for second active task")


def test_task_runner_cancel_matches_active_task(monkeypatch) -> None:
    """TaskRunner.cancel should request cancellation for a matching active task."""
    monkeypatch.setattr("cloudscope.task_runner.ui.timer", lambda *_args, **_kwargs: FakeTimer())
    runner = TaskRunner(EventBus())
    task_id = runner.start(task_kind=TaskKind.ANALYSIS, task_label="Analysis", worker=lambda _ctx: None)

    assert runner.cancel(task_kind=TaskKind.ANALYSIS, task_id=task_id)
    assert not runner.cancel(task_kind=TaskKind.SAVE, task_id=task_id)


def test_task_runner_terminal_progress_before_busy_false() -> None:
    """Terminal progress should publish before AppBusyChanged(False)."""
    bus = EventBus()
    events = []
    bus.subscribe(TaskProgressChanged, lambda event: events.append(event))
    bus.subscribe(AppBusyChanged, lambda event: events.append(event))
    runner = TaskRunner(bus)
    runner._active_task_id = "abc"  # test queue drain directly without NiceGUI timer
    runner._active_task_kind = TaskKind.ANALYSIS
    import queue

    runner._queue = queue.Queue()
    runner._queue.put(TaskRunnerMessage(kind=TaskRunnerMessageKind.COMPLETED, message="done"))

    runner.drain_messages(task_kind=TaskKind.ANALYSIS, task_id="abc", task_label="Analysis")

    assert isinstance(events[0], TaskProgressChanged)
    assert events[0].status is TaskStatus.COMPLETED
    assert isinstance(events[1], AppBusyChanged)
    assert events[1].is_busy is False
