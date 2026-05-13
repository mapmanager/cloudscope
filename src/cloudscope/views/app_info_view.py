"""Application information view for CloudScope."""

from __future__ import annotations

from nicegui import ui

from cloudscope.build_info import get_build_info_rows
from cloudscope.event_bus import EventBus
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId


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

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the application information card.

        Args:
            parent: Optional NiceGUI parent to build inside.

        Returns:
            Root element for this view.
        """
        if parent is None:
            with ui.column().classes('w-full') as self.root:
                self._build_card()
        else:
            with parent:
                with ui.column().classes('w-full') as self.root:
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

    def _build_rows(self) -> None:
        """Build build-info rows in the current NiceGUI slot.

        Returns:
            None.
        """
        for label, value in get_build_info_rows():
            with ui.row().classes('w-full items-start gap-2'):
                ui.label(label).classes('text-xs font-semibold text-gray-500 w-28 shrink-0')
                ui.label(value).classes('text-xs font-mono break-all')
