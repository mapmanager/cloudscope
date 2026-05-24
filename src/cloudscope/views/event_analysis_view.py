"""Left-toolbar view for AcqImage event CRUD."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui

from cloudscope.event_bus import EventBus
from cloudscope.events import (
    AcqImageEventsChanged,
    AcqImageEventSelectionChanged,
    AcqImageEventsVisibilityChanged,
    BeginAddAcqImageEventIntent,
    CancelAddAcqImageEventIntent,
    DeleteSelectedAcqImageEventIntent,
    SelectAcqImageEventIntent,
    SetAcqImageEventsVisibleIntent,
)
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.table_widget.column_def import ColumnDef
from nicewidgets.table_widget.config import TableWidgetConfig
from nicewidgets.table_widget.table_widget import TableWidget


class EventControlsCard:
    """Reusable controls for event CRUD actions.

    Args:
        on_add: Callback for add event.
        on_delete: Callback for delete selected event.
        on_select_next: Callback for select-next event.
        on_cancel: Callback for cancel current event action.
        on_visibility_changed: Callback receiving overlay visibility.
    """

    def __init__(
        self,
        *,
        on_add: Callable[[], None],
        on_delete: Callable[[], None],
        on_select_next: Callable[[], None],
        on_cancel: Callable[[], None],
        on_visibility_changed: Callable[[bool], None],
    ) -> None:
        self._on_add = on_add
        self._on_delete = on_delete
        self._on_select_next = on_select_next
        self._on_cancel = on_cancel
        self._on_visibility_changed = on_visibility_changed
        self._visible_checkbox: ui.checkbox | None = None

    def build(self) -> ui.card:
        """Build the controls card.

        Returns:
            Root card element.
        """
        with ui.card().classes("w-full gap-2") as card:
            ui.label("Events").classes("font-semibold")
            with ui.row().classes("w-full gap-2"):
                ui.button(icon="add", on_click=self._on_add).props("dense round").tooltip("Add event")
                ui.button(icon="delete", on_click=self._on_delete).props("dense round").tooltip("Delete selected event")
                ui.button(icon="skip_next", on_click=self._on_select_next).props("dense round").tooltip("Select next event")
                ui.button(icon="close", on_click=self._on_cancel).props("dense round").tooltip("Cancel")
            self._visible_checkbox = ui.checkbox(
                "Show events",
                value=True,
                on_change=lambda event: self._on_visibility_changed(bool(event.value)),
            )
        return card

    def set_visible_checked(self, visible: bool) -> None:
        """Set checkbox state without changing layout.

        Args:
            visible: Whether events are visible.
        """
        if self._visible_checkbox is None:
            return
        self._visible_checkbox.value = bool(visible)
        self._visible_checkbox.update()


class EventAnalysisView(BaseView):
    """Left-panel CRUD view for AcqImage events."""

    view_id = ViewId.EVENT_ANALYSIS
    disable_when_busy = False

    def __init__(
        self,
        event_bus: EventBus,
        app_state: Any | None = None,
        *,
        initially_visible: bool = True,
    ) -> None:
        """Create the event-analysis view.

        Args:
            event_bus: Page-scoped event bus.
            app_state: Home-page state object.
            initially_visible: Whether this view starts visible.
        """
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self._controls: EventControlsCard | None = None
        self._table: TableWidget | None = None
        self._rows: list[dict[str, object]] = []
        self._selected_event_id: int | None = None
        self._events_visible = True

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the view.

        Args:
            parent: Optional parent element.

        Returns:
            Root element.
        """
        if parent is None:
            self.root = ui.column().classes("w-full h-full min-h-0 gap-2")
        else:
            with parent:
                self.root = ui.column().classes("w-full h-full min-h-0 gap-2")
        with self.root:
            self._controls = EventControlsCard(
                on_add=self._add_event,
                on_delete=self._delete_selected,
                on_select_next=self._select_next,
                on_cancel=self._cancel,
                on_visibility_changed=self._set_events_visible,
            )
            self._controls.build()
            with ui.column().classes("w-full min-h-0 flex-1") as table_parent:
                self._table = TableWidget(
                    columns=_event_columns(),
                    row_id_field="id",
                    rows=[],
                    on_row_selected=self._on_row_selected,
                    config=TableWidgetConfig(selection_mode="single", show_index_column=False),
                )
                self._table.build(table_parent)
        self.after_build()
        return self.root

    def subscribe_events(self) -> None:
        """Subscribe to event-analysis state events."""
        self.add_subscription(self.event_bus.subscribe(AcqImageEventsChanged, self._on_events_changed))
        self.add_subscription(self.event_bus.subscribe(AcqImageEventSelectionChanged, self._on_selection_changed))
        self.add_subscription(self.event_bus.subscribe(AcqImageEventsVisibilityChanged, self._on_visibility_changed))

    def on_primary_selection_changed(self) -> None:
        """Clear local table rows when primary selection changes."""
        self._rows = []
        self._selected_event_id = None
        self._refresh_table()

    def _add_event(self) -> None:
        """Publish add-event intent for current selection."""
        self.event_bus.publish(BeginAddAcqImageEventIntent(selection=self._copy_selection()))

    def _delete_selected(self) -> None:
        """Publish delete-selected intent."""
        self.event_bus.publish(DeleteSelectedAcqImageEventIntent())

    def _select_next(self) -> None:
        """Select next event row, wrapping at end."""
        if not self._rows:
            self.event_bus.publish(SelectAcqImageEventIntent(event_id=None))
            return
        ids = [int(row["event_id"]) for row in self._rows]
        if self._selected_event_id not in ids:
            next_id = ids[0]
        else:
            idx = ids.index(int(self._selected_event_id))
            next_id = ids[(idx + 1) % len(ids)]
        self.event_bus.publish(SelectAcqImageEventIntent(event_id=next_id))

    def _cancel(self) -> None:
        """Publish cancel-add intent."""
        self.event_bus.publish(CancelAddAcqImageEventIntent())

    def _set_events_visible(self, visible: bool) -> None:
        """Publish event visibility intent."""
        self.event_bus.publish(SetAcqImageEventsVisibleIntent(visible=visible))

    def _on_row_selected(self, row: dict[str, Any]) -> None:
        """Publish event selection from table row selection.

        Args:
            row: Selected table row.
        """
        event_id = int(row["event_id"])
        self.event_bus.publish(SelectAcqImageEventIntent(event_id=event_id))

    def _on_events_changed(self, event: AcqImageEventsChanged) -> None:
        """Refresh rows from event state.

        Args:
            event: Events-changed state event.
        """
        if event.selection.file_id != self.current_selection.file_id:
            return
        if event.selection.channel != self.current_selection.channel:
            return
        if event.selection.roi_id != self.current_selection.roi_id:
            return
        self._rows = [dict(row) for row in event.rows]
        self._selected_event_id = event.selected_event_id
        self._events_visible = event.visible
        self._refresh_table()
        self._refresh_controls()

    def _on_selection_changed(self, event: AcqImageEventSelectionChanged) -> None:
        """Apply selected event id to table.

        Args:
            event: Selection state event.
        """
        self._selected_event_id = event.selected_event_id
        self._select_table_row()

    def _on_visibility_changed(self, event: AcqImageEventsVisibilityChanged) -> None:
        """Apply visibility checkbox state.

        Args:
            event: Visibility state event.
        """
        self._events_visible = event.visible
        self._refresh_controls()

    def _refresh_table(self) -> None:
        """Refresh table rows and selection."""
        if self._table is None:
            return
        self._table.set_data(self._rows)
        self._select_table_row()

    def _select_table_row(self) -> None:
        """Programmatically select current row in table."""
        if self._table is None:
            return
        if self._selected_event_id is None:
            self._table.clear_selection()
        else:
            self._table.set_selected_row_ids([str(self._selected_event_id)])

    def _refresh_controls(self) -> None:
        """Refresh controls state."""
        if self._controls is not None:
            self._controls.set_visible_checked(self._events_visible)

    def _copy_selection(self):
        """Return current selection copy."""
        from cloudscope.state import PrimarySelection

        return PrimarySelection(
            file_id=self.current_selection.file_id,
            channel=self.current_selection.channel,
            roi_id=self.current_selection.roi_id,
        )


def _event_columns() -> tuple[ColumnDef, ...]:
    """Return event table column definitions."""
    return (
        ColumnDef("id", "ID"),
        ColumnDef("event_type", "Type"),
        ColumnDef("x0", "x0", extra={"type": "numericColumn"}),
        ColumnDef("x1", "x1", extra={"type": "numericColumn"}),
        ColumnDef("duration", "Duration", extra={"type": "numericColumn"}),
    )
