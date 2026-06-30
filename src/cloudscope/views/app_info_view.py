"""Application information view for CloudScope."""

from __future__ import annotations

import os

from nicegui import ui

from cloudscope.build_info import get_build_info_rows
from cloudscope.event_bus import EventBus
from cloudscope.utils.file_manager import open_path_with_default_app
from cloudscope.utils.logging import get_log_file_path, read_log_tail
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.smart_expansion_widget.smart_expansion import SmartExpansion


class AppInfoView(BaseView):
    """Display runtime application and build information.

    Args:
        event_bus: Page-scoped event bus.
        initially_visible: Whether the view starts visible.
    """

    view_id = ViewId.APP_INFO
    disable_when_busy = False

    def __init__(self, *, event_bus: EventBus, initially_visible: bool = False) -> None:
        super().__init__(event_bus=event_bus, app_state=None, initially_visible=initially_visible)
        self._rows_column: ui.column | None = None
        self._log_textarea: ui.textarea | None = None

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the application information card.

        Args:
            parent: Optional NiceGUI parent to build inside.

        Returns:
            Root element for this view.
        """
        root_classes = 'w-full h-full min-h-0 flex-1 overflow-y-auto pr-1'
        if parent is None:
            with ui.column().classes(root_classes) as self.root:
                self._build_card()
        else:
            with parent:
                with ui.column().classes(root_classes) as self.root:
                    self._build_card()
        self.after_build()
        return self.root

    def refresh_from_state(self) -> None:
        """Refresh displayed build information.

        Returns:
            None.
        """
        if self._rows_column is None:
            return
        self._rows_column.clear()
        with self._rows_column:
            self._build_rows()

    def _build_card(self) -> None:
        """Build the static card structure.

        Returns:
            None.
        """
        with ui.card().classes('w-full gap-3'):
            ui.label('App information').classes('text-lg font-semibold')
            ui.label('Build and release metadata for this CloudScope runtime.').classes('text-sm text-gray-600')
            with ui.column().classes('w-full gap-1') as rows_column:
                self._rows_column = rows_column
                self._build_rows()
            self._build_log_controls()

    def _build_log_controls(self) -> None:
        """Build log open button and recent-log preview expansion.

        Returns:
            None.
        """
        open_logs_button = ui.button('Open Logs', on_click=self._on_open_logs_clicked)
        if not self._can_open_log_file():
            open_logs_button.disable()

        log_expansion = SmartExpansion(
            'Cloudscope logs',
            # icon='article',
            # caption='cloudscope.log',
            initially_open=False,
            on_open=self._refresh_log_preview,
        )
        with log_expansion:
            self._log_textarea = ui.textarea(value='').classes('w-full font-mono text-xs')
            self._log_textarea.props('readonly rows=20')
        log_expansion.apply_initial_state()

    def _refresh_log_preview(self) -> None:
        """Load the CloudScope log tail into the preview textarea.

        Returns:
            None.
        """
        if self._log_textarea is None:
            return
        self._log_textarea.value = read_log_tail(max_lines=200)

    def _on_open_logs_clicked(self) -> None:
        """Open the CloudScope log file in the OS default application.

        Returns:
            None.
        """
        path = get_log_file_path()
        if path is None:
            ui.notify('File logging is not enabled.', type='warning')
            return
        try:
            open_path_with_default_app(path)
        except FileNotFoundError:
            ui.notify('Log file is not available yet.', type='warning')
        except OSError as exc:
            ui.notify(f'Unable to open log file: {exc}', type='negative')

    @classmethod
    def _can_open_log_file(cls) -> bool:
        """Return whether the current runtime can open the log file locally.

        Returns:
            False on remote/server deployments where opening a host file would
            not help browser users; True for local desktop and Python runs.
        """
        value = os.getenv('CLOUDSCOPE_REMOTE', '').strip().lower()
        return value not in {'1', 'true', 'yes', 'on'}

    def _build_rows(self) -> None:
        """Build build-info rows in the current NiceGUI slot.

        Returns:
            None.
        """
        for label, value in get_build_info_rows():
            with ui.row().classes('w-full items-start gap-2'):
                ui.label(label).classes('text-xs font-semibold text-gray-500 w-28 shrink-0')
                ui.label(value).classes('text-xs font-mono break-all')
