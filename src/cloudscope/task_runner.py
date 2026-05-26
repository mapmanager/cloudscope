"""Single-active-task runner for CloudScope long-running work."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import uuid4

from nicegui import ui

from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import (
    AppBusyChanged,
    TaskKind,
    TaskProgressChanged,
    TaskStatus,
)
from cloudscope.events.status import AppStatusChanged, StatusLevel, StatusSource


class TaskRunnerMessageKind(StrEnum):
    """Internal worker-to-UI message kinds."""

    PROGRESS = "progress"
    EVENT = "event"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class TaskRunnerMessage:
    """Internal message emitted by a running worker.

    Args:
        kind: Message kind.
        fraction: Optional fraction complete in [0, 1].
        message: Human-readable message.
        event: Optional event object to publish on the UI thread.
        result: Optional worker result.
        error: Optional worker exception.
    """

    kind: TaskRunnerMessageKind
    fraction: float | None = None
    message: str = ""
    event: Any | None = None
    result: Any | None = None
    error: BaseException | None = None


class TaskContext:
    """Context passed to long-running worker functions.

    Args:
        task_id: Unique task identifier.
        task_kind: Task category.
        queue_: Queue used to report worker messages to the NiceGUI thread.
        cancel_event: Event set when cancellation has been requested.
    """

    def __init__(
        self,
        *,
        task_id: str,
        task_kind: TaskKind,
        queue_: queue.Queue[TaskRunnerMessage],
        cancel_event: threading.Event,
    ) -> None:
        self.task_id = task_id
        self.task_kind = task_kind
        self._queue = queue_
        self._cancel_event = cancel_event

    def report_progress(self, fraction: float | None, message: str = "") -> None:
        """Report progress from worker code.

        Args:
            fraction: Fraction complete in [0, 1], or None if unknown.
            message: Human-readable message.

        Returns:
            None.
        """
        self._queue.put(
            TaskRunnerMessage(
                kind=TaskRunnerMessageKind.PROGRESS,
                fraction=fraction,
                message=message,
            )
        )

    def report_event(self, event: Any) -> None:
        """Queue an event to publish on the NiceGUI thread.

        Args:
            event: Event object to publish through the page event bus.

        Returns:
            None.
        """
        self._queue.put(
            TaskRunnerMessage(
                kind=TaskRunnerMessageKind.EVENT,
                event=event,
            )
        )

    @property
    def cancel_event(self) -> threading.Event:
        """Return the shared cancellation event for cooperative workers.

        Returns:
            Event set by ``TaskRunner.cancel`` when cancellation is requested.
        """
        return self._cancel_event

    def is_cancelled(self) -> bool:
        """Return whether cancellation has been requested.

        Returns:
            True if cancellation has been requested.
        """
        return self._cancel_event.is_set()

    def raise_if_cancelled(self) -> None:
        """Raise ``TaskCancelled`` if cancellation was requested.

        Raises:
            TaskCancelled: If cancellation has been requested.
        """
        if self.is_cancelled():
            raise TaskCancelled("Task cancelled")


class TaskCancelled(RuntimeError):
    """Raised by worker code to indicate cooperative cancellation."""


class TaskRunner:
    """Run one long-running task at a time.

    Expensive worker code runs in a background thread. Worker progress is sent
    through a queue and drained on the NiceGUI thread, where task events are
    published. Only one task may be active at a time.

    Args:
        event_bus: Page-scoped event bus.
        timer_interval_s: Interval used by the NiceGUI queue-drain timer.
    """

    def __init__(self, event_bus: EventBus, *, timer_interval_s: float = 0.1) -> None:
        self._event_bus = event_bus
        self._timer_interval_s = float(timer_interval_s)
        self._active_task_id: str | None = None
        self._active_task_kind: TaskKind | None = None
        self._cancel_event: threading.Event | None = None
        self._queue: queue.Queue[TaskRunnerMessage] | None = None
        self._timer = None

    @property
    def active_task_id(self) -> str | None:
        """Return the active task id, if any.

        Returns:
            Active task id or None.
        """
        return self._active_task_id

    @property
    def active_task_kind(self) -> TaskKind | None:
        """Return the active task kind, if any.

        Returns:
            Active task kind or None.
        """
        return self._active_task_kind

    def is_running(self) -> bool:
        """Return whether a task is active.

        Returns:
            True if a task is active.
        """
        return self._active_task_id is not None

    def start(
        self,
        *,
        task_kind: TaskKind,
        task_label: str,
        worker: Callable[[TaskContext], Any],
        on_completed: Callable[[Any], None] | None = None,
        on_failed: Callable[[BaseException], None] | None = None,
        on_cancelled: Callable[[], None] | None = None,
    ) -> str:
        """Start one background task.

        Args:
            task_kind: Task category.
            task_label: Human-readable label for progress events.
            worker: Callable run in a background thread. It receives a
                ``TaskContext``.
            on_completed: Optional callback run on the NiceGUI thread when the
                task completes successfully.
            on_failed: Optional callback run on the NiceGUI thread when the task
                fails.
            on_cancelled: Optional callback run on the NiceGUI thread when the
                task is cancelled.

        Returns:
            New task id.

        Raises:
            RuntimeError: If another task is already running.
        """
        if self.is_running():
            raise RuntimeError("A task is already running")

        task_id = uuid4().hex
        cancel_event = threading.Event()
        messages: queue.Queue[TaskRunnerMessage] = queue.Queue()
        context = TaskContext(
            task_id=task_id,
            task_kind=task_kind,
            queue_=messages,
            cancel_event=cancel_event,
        )

        self._active_task_id = task_id
        self._active_task_kind = task_kind
        self._cancel_event = cancel_event
        self._queue = messages

        self._publish_busy(True, task_kind=task_kind, task_id=task_id, message=f"{task_label}: starting")
        self._publish_progress(task_kind, task_id, task_label, TaskStatus.QUEUED, 0, 100, "Queued")
        self._publish_progress(task_kind, task_id, task_label, TaskStatus.RUNNING, 0, 100, "Running")

        def run_worker() -> None:
            try:
                result = worker(context)
                if context.is_cancelled():
                    messages.put(TaskRunnerMessage(kind=TaskRunnerMessageKind.CANCELLED, message="Cancelled"))
                else:
                    messages.put(TaskRunnerMessage(kind=TaskRunnerMessageKind.COMPLETED, fraction=1.0, message="Completed", result=result))
            except TaskCancelled:
                messages.put(TaskRunnerMessage(kind=TaskRunnerMessageKind.CANCELLED, message="Cancelled"))
            except BaseException as exc:
                if context.is_cancelled():
                    messages.put(TaskRunnerMessage(kind=TaskRunnerMessageKind.CANCELLED, message="Cancelled", error=exc))
                else:
                    messages.put(TaskRunnerMessage(kind=TaskRunnerMessageKind.FAILED, message=str(exc), error=exc))

        thread = threading.Thread(target=run_worker, daemon=True)
        thread.start()

        self._timer = ui.timer(
            self._timer_interval_s,
            lambda: self.drain_messages(
                task_kind=task_kind,
                task_id=task_id,
                task_label=task_label,
                on_completed=on_completed,
                on_failed=on_failed,
                on_cancelled=on_cancelled,
            ),
        )
        return task_id

    def cancel(self, *, task_kind: TaskKind | None = None, task_id: str | None = None) -> bool:
        """Request cancellation of the active task.

        Args:
            task_kind: Optional expected task kind.
            task_id: Optional expected task id.

        Returns:
            True if cancellation was requested, False if no matching task is active.
        """
        if self._cancel_event is None or self._active_task_id is None:
            return False
        if task_kind is not None and self._active_task_kind != task_kind:
            return False
        if task_id is not None and self._active_task_id != task_id:
            return False
        self._cancel_event.set()
        self._event_bus.publish(
            AppStatusChanged(
                level=StatusLevel.INFO,
                message="Cancellation requested",
                source=StatusSource.SYSTEM,
            )
        )
        return True

    def drain_messages(
        self,
        *,
        task_kind: TaskKind,
        task_id: str,
        task_label: str,
        on_completed: Callable[[Any], None] | None = None,
        on_failed: Callable[[BaseException], None] | None = None,
        on_cancelled: Callable[[], None] | None = None,
    ) -> None:
        """Drain queued worker messages on the NiceGUI thread.

        Args:
            task_kind: Task kind for emitted events.
            task_id: Task id for emitted events.
            task_label: Human-readable task label.
            on_completed: Optional completion callback.
            on_failed: Optional failure callback.
            on_cancelled: Optional cancellation callback.

        Returns:
            None.
        """
        if self._queue is None:
            return

        while True:
            try:
                message = self._queue.get_nowait()
            except queue.Empty:
                return

            if message.kind == TaskRunnerMessageKind.PROGRESS:
                current = self._fraction_to_current(message.fraction)
                self._publish_progress(
                    task_kind,
                    task_id,
                    task_label,
                    TaskStatus.RUNNING,
                    current,
                    100,
                    message.message,
                )
                continue

            if message.kind == TaskRunnerMessageKind.EVENT:
                if message.event is not None:
                    self._event_bus.publish(message.event)
                continue

            if message.kind == TaskRunnerMessageKind.COMPLETED:
                self._publish_progress(
                    task_kind,
                    task_id,
                    task_label,
                    TaskStatus.COMPLETED,
                    100,
                    100,
                    message.message,
                )
                if on_completed is not None:
                    on_completed(message.result)
                self._finish_task(message="Task complete")
                return

            if message.kind == TaskRunnerMessageKind.CANCELLED:
                self._publish_progress(
                    task_kind,
                    task_id,
                    task_label,
                    TaskStatus.CANCELLED,
                    0,
                    100,
                    message.message,
                )
                if on_cancelled is not None:
                    on_cancelled()
                self._finish_task(message="Task cancelled")
                return

            if message.kind == TaskRunnerMessageKind.FAILED:
                self._publish_progress(
                    task_kind,
                    task_id,
                    task_label,
                    TaskStatus.FAILED,
                    0,
                    100,
                    message.message,
                )
                if on_failed is not None and message.error is not None:
                    on_failed(message.error)
                self._finish_task(message="Task failed")
                return
                
    def _finish_task(self, *, message: str) -> None:
        """Clear active task state after a terminal event.

        Args:
            message: Human-readable terminal message.

        Returns:
            None.
        """
        if self._timer is not None:
            try:
                self._timer.cancel()
            except AttributeError:
                pass
            self._timer = None
        self._active_task_id = None
        self._active_task_kind = None
        self._cancel_event = None
        self._queue = None
        self._publish_busy(False, task_kind=None, task_id=None, message=message)

    def _publish_busy(
        self,
        is_busy: bool,
        *,
        task_kind: TaskKind | None,
        task_id: str | None,
        message: str,
    ) -> None:
        """Publish app busy state.

        Args:
            is_busy: Whether a task is active.
            task_kind: Active task kind, if any.
            task_id: Active task id, if any.
            message: Human-readable message.

        Returns:
            None.
        """
        self._event_bus.publish(
            AppBusyChanged(
                is_busy=is_busy,
                task_kind=task_kind,
                task_id=task_id,
                message=message,
            )
        )

    def _publish_progress(
        self,
        task_kind: TaskKind,
        task_id: str,
        task_label: str,
        status: TaskStatus,
        current: int,
        total: int,
        message: str,
    ) -> None:
        """Publish task progress.

        Args:
            task_kind: Task kind.
            task_id: Task id.
            task_label: Human-readable task label.
            status: Task lifecycle status.
            current: Current progress count.
            total: Total progress count.
            message: Human-readable message.

        Returns:
            None.
        """
        self._event_bus.publish(
            TaskProgressChanged(
                task_kind=task_kind,
                task_id=task_id,
                task_label=task_label,
                status=status,
                current=current,
                total=total,
                message=message,
            )
        )

    @staticmethod
    def _fraction_to_current(fraction: float | None) -> int:
        """Convert optional fraction to integer progress.

        Args:
            fraction: Optional fraction complete.

        Returns:
            Integer progress in [0, 100].
        """
        if fraction is None:
            return 0
        return max(0, min(100, int(round(float(fraction) * 100))))
