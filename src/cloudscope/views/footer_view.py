"""Main-page footer: selection (file, channel, ROI) plus app status and task progress."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from nicegui import ui

from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import TaskProgressChanged
from cloudscope.events.status import AppStatusChanged
from cloudscope.utils.logging import get_logger
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId

logger = get_logger(__name__)

_FOOTER_PLACEHOLDER = '—'


def footer_display_values(
    file_id: str | None,
    channel: int | None,
    roi_id: int | None,
) -> tuple[str, str, str]:
    """Compute footer strings for file basename, channel, and ROI.

    Args:
        file_id: Current file identifier, or None.
        channel: Current channel index, or None.
        roi_id: Current ROI identifier, or None.

    Returns:
        ``(file, channel, roi)`` display strings.
    """
    if file_id is None:
        return (_FOOTER_PLACEHOLDER, _FOOTER_PLACEHOLDER, _FOOTER_PLACEHOLDER)
    basename = str(Path(file_id).name)
    ch = _FOOTER_PLACEHOLDER if channel is None else str(channel)
    roi = _FOOTER_PLACEHOLDER if roi_id is None else str(roi_id)
    return (basename, ch, roi)


class FooterView(BaseView):
    """NiceGUI footer: selection state plus latest app/status task line.

    Args:
        event_bus: Page-scoped event bus.
        app_state: Optional home-page state used when shown.
        initially_visible: Whether this view starts visible.
    """

    view_id = ViewId.FOOTER
    disable_when_busy = False

    def __init__(
        self,
        event_bus: EventBus,
        app_state: Any | None = None,
        *,
        initially_visible: bool = True,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self._client = None
        self._file_id: str | None = None
        self._channel: int | None = None
        self._roi_id: int | None = None
        self._file_label: ui.label | None = None
        self._channel_label: ui.label | None = None
        self._roi_label: ui.label | None = None
        self._status_label: ui.label | None = None

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Create ``ui.footer`` with file, channel, ROI, and status labels.

        Args:
            parent: Ignored. Footers must be built at page top level.

        Returns:
            Root footer element.
        """
        self._client = ui.context.client
        with ui.footer().classes(
            'w-full px-3 py-1 flex items-center bg-gray-900 text-gray-200'
        ) as self.root:
            with ui.row().classes('w-full items-center gap-6 min-w-0'):
                self._file_label = ui.label().classes('truncate max-w-[320px]')
                self._channel_label = ui.label().classes('truncate')
                self._roi_label = ui.label().classes('truncate')
                self._status_label = ui.label('Status: —').classes('truncate grow text-right')
        self.after_build()
        return self.root

    def subscribe_events(self) -> None:
        """Subscribe to footer state events while visible.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(AppStatusChanged, self._on_app_status_changed))
        self.add_subscription(self.event_bus.subscribe(TaskProgressChanged, self._on_task_progress_changed))

    def refresh_from_state(self) -> None:
        """Refresh footer selection text from cached BaseView state.

        Returns:
            None.
        """
        self._sync_selection_from_base()
        self._refresh_labels()

    def on_primary_selection_changed(self) -> None:
        """Refresh footer labels after the primary selection changes.

        Returns:
            None.
        """
        def apply() -> None:
            self._sync_selection_from_base()
            self._refresh_labels()

        self._run_ui(apply)

    def _sync_selection_from_base(self) -> None:
        """Copy BaseView cached selection into footer display fields.

        Returns:
            None.
        """
        self._file_id = self.current_selection.file_id
        self._channel = self.current_selection.channel
        self._roi_id = self.current_selection.roi_id

    def _run_ui(self, fn: Callable[[], None]) -> None:
        """Run UI updates, remarshal via ``Client.safe_invoke`` when needed.

        Args:
            fn: UI update callable.

        Returns:
            None.
        """
        try:
            fn()
        except RuntimeError as exc:
            message = str(exc).lower()
            if 'slot' not in message and 'client' not in message:
                raise
            if self._client is None:
                logger.warning('Footer UI update dropped (no client): %s', exc)
                return
            self._client.safe_invoke(fn)




    def _refresh_labels(self) -> None:
        """Push cached selection into footer labels.

        Returns:
            None.
        """
        if self._file_label is None or self._channel_label is None or self._roi_label is None:
            return
        file_s, ch_s, roi_s = footer_display_values(self._file_id, self._channel, self._roi_id)
        self._file_label.text = f'File: {file_s}'
        self._channel_label.text = f'Channel: {ch_s}'
        self._roi_label.text = f'ROI: {roi_s}'

    def _on_app_status_changed(self, event: AppStatusChanged) -> None:
        """Render latest app-level status in footer.

        Args:
            event: App status state event.

        Returns:
            None.
        """
        def apply() -> None:
            if self._status_label is None:
                return
            color = {
                'info': 'text-blue-300',
                'warning': 'text-yellow-300',
                'error': 'text-red-300',
            }.get(event.level.value, 'text-gray-200')
            self._status_label.text = f'Status: {event.message}'
            self._status_label.classes(replace=f'truncate grow text-right {color}')

        self._run_ui(apply)

    def _on_task_progress_changed(self, event: TaskProgressChanged) -> None:
        """Render latest task progress in footer.

        Args:
            event: Task progress state event.

        Returns:
            None.
        """
        def apply() -> None:
            if self._status_label is None:
                return
            self._status_label.text = f'Status: {event.task_label} - {event.message}'

        self._run_ui(apply)
