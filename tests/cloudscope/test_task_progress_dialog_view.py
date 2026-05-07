"""Tests for the generic task progress dialog view."""

from __future__ import annotations

from cloudscope.event_bus import EventBus
from cloudscope.events import CancelTaskIntent, TaskKind, TaskProgressChanged, TaskStatus
from cloudscope.views.task_progress_dialog_view import TaskProgressDialogView


class _Dialog:
    """Fake dialog tracking open/close state."""

    def __init__(self) -> None:
        self.opened = False

    def open(self) -> None:
        """Mark the dialog open."""
        self.opened = True

    def close(self) -> None:
        """Mark the dialog closed."""
        self.opened = False


class _Label:
    """Fake label with text."""

    def __init__(self) -> None:
        self.text = ''


class _Progress:
    """Fake progress bar with value."""

    def __init__(self) -> None:
        self.value = 0.0


class _Button:
    """Fake button tracking visibility/enabled state."""

    def __init__(self) -> None:
        self.visible = False
        self.enabled = False
        self.updated = 0

    def update(self) -> None:
        """Record updates."""
        self.updated += 1


def _configured_view(bus: EventBus) -> TaskProgressDialogView:
    """Return a dialog view with fake UI controls installed."""
    view = TaskProgressDialogView(event_bus=bus)
    view._dialog = _Dialog()  # type: ignore[assignment]
    view._label = _Label()  # type: ignore[assignment]
    view._message = _Label()  # type: ignore[assignment]
    view._progress = _Progress()  # type: ignore[assignment]
    view._cancel_button = _Button()  # type: ignore[assignment]
    view.subscribe_events()
    return view


def test_task_progress_dialog_opens_and_closes() -> None:
    """Queued/running opens the dialog and terminal status closes it."""
    bus = EventBus()
    view = _configured_view(bus)

    bus.publish(
        TaskProgressChanged(
            task_kind=TaskKind.LOAD,
            task_id='1',
            task_label='Load file',
            status=TaskStatus.RUNNING,
            current=1,
            total=4,
            message='Step',
        )
    )

    assert view._dialog.opened is True
    assert view._progress.value == 0.25
    assert view._cancel_button.visible is True
    assert view.current_task_id == '1'

    bus.publish(
        TaskProgressChanged(
            task_kind=TaskKind.LOAD,
            task_id='1',
            task_label='Load file',
            status=TaskStatus.COMPLETED,
            current=4,
            total=4,
            message='Done',
        )
    )

    assert view._dialog.opened is False
    assert view._cancel_button.visible is False
    assert view.current_task_id is None


def test_task_progress_dialog_cancel_publishes_intent() -> None:
    """Cancel button should publish CancelTaskIntent for the displayed task."""
    bus = EventBus()
    published: list[CancelTaskIntent] = []
    bus.subscribe(CancelTaskIntent, published.append)
    view = _configured_view(bus)
    bus.publish(
        TaskProgressChanged(
            task_kind=TaskKind.ANALYSIS,
            task_id='abc',
            task_label='Analysis',
            status=TaskStatus.RUNNING,
            current=1,
            total=10,
            message='Running',
        )
    )

    view._on_cancel_clicked()

    assert published == [CancelTaskIntent(task_kind=TaskKind.ANALYSIS, task_id='abc')]
