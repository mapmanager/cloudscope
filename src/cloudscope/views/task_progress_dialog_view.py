"""Generic modal task-progress dialog for CloudScope long-running tasks."""

from __future__ import annotations

from nicegui import ui

from cloudscope.event_bus import EventBus
from cloudscope.events import CancelTaskIntent, TaskKind, TaskProgressChanged, TaskStatus
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId


class TaskProgressDialogView(BaseView):
    """Show progress and cancellation controls for the active long task.

    This view is the single task-cancellation UI for long-running CloudScope
    work. It observes ``TaskProgressChanged`` events, opens a modal progress
    dialog while a task is queued/running, and emits ``CancelTaskIntent`` when
    the user clicks Cancel.

    Args:
        event_bus: Page-scoped event bus.
        initially_visible: Whether this view starts visible. The view root is a
            small invisible container; the dialog opens only when tasks run.
    """

    view_id = ViewId.TASK_PROGRESS_DIALOG
    disable_when_busy = False

    def __init__(self, event_bus: EventBus, *, initially_visible: bool = True) -> None:
        super().__init__(event_bus=event_bus, app_state=None, initially_visible=initially_visible)
        self._dialog: ui.dialog | None = None
        self._label: ui.label | None = None
        self._message: ui.label | None = None
        self._progress: ui.linear_progress | None = None
        self._cancel_button: ui.button | None = None
        self._current_task_kind: TaskKind | None = None
        self._current_task_id: str | None = None

    @property
    def current_task_id(self) -> str | None:
        """Return the task id currently shown by the dialog.

        Returns:
            Current task id, or None when no cancellable task is shown.
        """
        return self._current_task_id

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the task progress dialog.

        Args:
            parent: Optional NiceGUI parent for the invisible root container.

        Returns:
            Root element for this view.
        """
        def _build() -> None:
            with ui.element("div").classes("hidden") as self.root:
                pass
            with ui.dialog() as dialog, ui.card().classes("w-[460px]"):
                self._label = ui.label("Task").classes("text-lg font-semibold")
                self._message = ui.label("").classes("text-sm text-gray-600")
                self._progress = ui.linear_progress(value=0.0).classes("w-full")
                with ui.row().classes("w-full justify-end"):
                    self._cancel_button = ui.button(
                        "Cancel",
                        on_click=self._on_cancel_clicked,
                    ).props("outline color=negative")
            self._dialog = dialog

        if parent is None:
            _build()
        else:
            with parent:
                _build()

        self.after_build()
        return self.root

    def subscribe_events(self) -> None:
        """Subscribe to task progress events while this view is visible.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(TaskProgressChanged, self._on_task_progress_changed))

    def _on_task_progress_changed(self, event: TaskProgressChanged) -> None:
        """Update progress dialog from a task-progress event.

        Args:
            event: Task progress state event.

        Returns:
            None.
        """
        if (
            self._dialog is None
            or self._label is None
            or self._message is None
            or self._progress is None
            or self._cancel_button is None
        ):
            return

        self._label.text = event.task_label
        self._message.text = event.message
        denom = 1 if event.total <= 0 else event.total
        self._progress.value = min(1.0, max(0.0, event.current / denom))

        if event.status in (TaskStatus.QUEUED, TaskStatus.RUNNING):
            self._current_task_kind = event.task_kind
            self._current_task_id = event.task_id
            self._cancel_button.visible = True
            self._cancel_button.enabled = True
            self._cancel_button.update()
            self._dialog.open()
            return

        self._current_task_kind = None
        self._current_task_id = None
        self._cancel_button.visible = False
        self._cancel_button.enabled = False
        self._cancel_button.update()
        self._dialog.close()

    def _on_cancel_clicked(self) -> None:
        """Publish a cancellation intent for the currently displayed task.

        Returns:
            None.
        """
        if self._current_task_kind is None:
            return
        self.event_bus.publish(
            CancelTaskIntent(
                task_kind=self._current_task_kind,
                task_id=self._current_task_id,
            )
        )
