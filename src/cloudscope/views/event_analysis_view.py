"""Left-toolbar view for AcqImage event CRUD."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui

from acqstore.acq_image.analysis.model import AnalysisKey
from cloudscope.event_bus import EventBus
from cloudscope.events.acq_image_events import (
    AcqImageEventsChanged,
    AcqImageEventSelectionChanged,
    BeginAddAcqImageEventIntent,
    BeginEditAcqImageEventIntent,
    CancelAddAcqImageEventIntent,
    DeleteSelectedAcqImageEventIntent,
    EventEditMode,
    RequestAcqImageEventsRefreshIntent,
    SelectAcqImageEventIntent,
    SetAcqImageEventsVisibleIntent,
)
from cloudscope.events.analysis import AnalysisCompleted, AnalysisKind, RunAnalysisIntent
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.table_widget.column_def import ColumnDef
from nicewidgets.table_widget.config import TableWidgetConfig, scaled_row_header_heights_px
from nicewidgets.table_widget.table_widget import TableWidget


def _load_event_analysis_class() -> type[Any] | None:
    """Load the AcqStore event analysis class.

    Returns:
        ``EventAnalysis`` class when available, otherwise None.
    """
    try:
        from acqstore.acq_image.analysis.event_analysis.event_analysis import EventAnalysis
    except Exception:
        return None
    return EventAnalysis


class EventControlsCard:
    """Reusable controls for event CRUD actions.

    Args:
        on_add: Callback for add event.
        on_edit: Callback for edit selected event.
        on_delete: Callback for delete selected event.
        on_select_next: Callback for select-next event.
        on_cancel: Callback for cancel current event action.
        on_visibility_changed: Callback receiving overlay visibility.
        on_run: Callback for event-stat reanalysis.
    """

    def __init__(
        self,
        *,
        on_add: Callable[[], None],
        on_edit: Callable[[], None],
        on_delete: Callable[[], None],
        on_select_next: Callable[[], None],
        on_cancel: Callable[[], None],
        on_visibility_changed: Callable[[bool], None],
        on_run: Callable[[], None],
    ) -> None:
        self._on_add = on_add
        self._on_edit = on_edit
        self._on_delete = on_delete
        self._on_select_next = on_select_next
        self._on_cancel = on_cancel
        self._on_visibility_changed = on_visibility_changed
        self._on_run = on_run
        self._add_button: ui.button | None = None
        self._edit_button: ui.button | None = None
        self._delete_button: ui.button | None = None
        self._select_next_button: ui.button | None = None
        self._cancel_button: ui.button | None = None
        self._visible_checkbox: ui.checkbox | None = None
        self._run_button: ui.button | None = None
        self._updating_checkbox = False

    def build(self) -> ui.card:
        """Build the controls card.

        Returns:
            Root card element.
        """
        with ui.card().classes("w-full gap-2") as card:
            ui.label("Events").classes("font-semibold")
            with ui.row().classes("w-full gap-2 items-center"):
                self._add_button = ui.button(icon="add", on_click=self._on_add).props("dense round")
                self._add_button.tooltip("Add event")
                self._edit_button = ui.button(icon="edit", on_click=self._on_edit).props("dense round")
                self._edit_button.tooltip("Edit selected event")
                self._delete_button = ui.button(icon="delete", on_click=self._on_delete).props("dense round")
                self._delete_button.tooltip("Delete selected event")
                self._select_next_button = ui.button(icon="skip_next", on_click=self._on_select_next).props("dense round")
                self._select_next_button.tooltip("Select next event")
                self._cancel_button = ui.button(icon="close", on_click=self._on_cancel).props("dense round")
                self._cancel_button.tooltip("Cancel add/edit")
            self._visible_checkbox = ui.checkbox(
                "Show events",
                value=True,
                on_change=self._handle_visibility_changed,
            )
            self._run_button = ui.button("Run/Reanalyze Events", on_click=self._on_run).classes("w-full")
        self.set_controls_state(has_rows=False, has_selection=False, is_editing=False, can_run=False)
        return card

    def set_visible_checked(self, visible: bool) -> None:
        """Set checkbox state without emitting an intent.

        Args:
            visible: Whether events are visible.
        """
        if self._visible_checkbox is None:
            return
        self._updating_checkbox = True
        try:
            self._visible_checkbox.value = bool(visible)
            self._visible_checkbox.update()
        finally:
            self._updating_checkbox = False

    def set_controls_state(
        self,
        *,
        has_rows: bool,
        has_selection: bool,
        is_editing: bool,
        can_run: bool,
    ) -> None:
        """Enable or disable controls for the current event state.

        Args:
            has_rows: Whether the current event table has rows.
            has_selection: Whether an event is selected.
            is_editing: Whether add/edit is waiting for a plot x-range.
            can_run: Whether event analysis can be run for the selection.
        """
        if self._add_button is not None:
            self._add_button.enabled = not is_editing
            self._add_button.update()
        if self._edit_button is not None:
            self._edit_button.enabled = bool(has_selection and not is_editing)
            self._edit_button.update()
        if self._delete_button is not None:
            self._delete_button.enabled = bool(has_selection and not is_editing)
            self._delete_button.update()
        if self._select_next_button is not None:
            self._select_next_button.enabled = bool(has_rows and not is_editing)
            self._select_next_button.update()
        if self._cancel_button is not None:
            self._cancel_button.enabled = bool(is_editing)
            self._cancel_button.update()
        if self._run_button is not None:
            self._run_button.enabled = bool(can_run and not is_editing)
            self._run_button.update()

    def _handle_visibility_changed(self, event: Any) -> None:
        """Forward user-driven visibility changes.

        Args:
            event: NiceGUI checkbox event.
        """
        if self._updating_checkbox:
            return
        self._on_visibility_changed(bool(event.value))


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
        table_font_size_px: int = 12,
    ) -> None:
        """Create the event-analysis view.

        Args:
            event_bus: Page-scoped event bus.
            app_state: Home-page state object.
            initially_visible: Whether this view starts visible.
            table_font_size_px: Table cell font size in pixels.
        """
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self._controls: EventControlsCard | None = None
        self._table_font_size_px = int(table_font_size_px)
        self._table: TableWidget | None = None
        self._rows: list[dict[str, object]] = []
        self._selected_event_id: int | None = None
        self._events_visible = True
        self._edit_mode = EventEditMode.NONE
        self._range_notification: Any | None = None
        self._range_notification_message: str | None = None
        self._params_container: ui.column | None = None
        self._results_container: ui.column | None = None
        self._param_controls: dict[str, Any] = {}

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
                on_edit=self._edit_event,
                on_delete=self._delete_selected,
                on_select_next=self._select_next,
                on_cancel=self._cancel,
                on_visibility_changed=self._set_events_visible,
                on_run=self._run_event_analysis,
            )
            self._controls.build()
            self._params_container = ui.column().classes("w-full gap-2")
            self._build_param_controls()
            self._results_container = ui.column().classes("w-full gap-2")
            self._build_results_controls()
            with ui.column().classes("w-full min-w-0 min-h-0 flex-1") as table_parent:
                font_px = int(self._table_font_size_px)
                row_h, header_h = scaled_row_header_heights_px(font_px)
                self._table = TableWidget(
                    columns=_event_columns(),
                    row_id_field="id",
                    rows=[],
                    on_row_selected=self._on_row_selected,
                    config=TableWidgetConfig(
                        selection_mode="single",
                        show_index_column=False,
                        cell_font_size_px=font_px,
                        row_height=row_h,
                        header_height=header_h,
                        fit_columns_on_grid_resize=True,
                        extra_grid_options={
                            "defaultColDef": {
                                "filter": False,
                            },
                        },
                    ),
                )
                self._table.build(table_parent)
        self.after_build()
        return self.root

    def subscribe_events(self) -> None:
        """Subscribe to event-analysis state events."""
        self.add_subscription(self.event_bus.subscribe(AcqImageEventsChanged, self._on_events_changed))
        self.add_subscription(self.event_bus.subscribe(AcqImageEventSelectionChanged, self._on_selection_changed))
        self.add_subscription(self.event_bus.subscribe(AnalysisCompleted, self._on_analysis_completed))

    def refresh_from_state(self) -> None:
        """Request current event rows for the active selection."""
        self._request_events_refresh()

    def on_primary_selection_changed(self) -> None:
        """Refresh table rows when primary selection changes."""
        self._rows = []
        self._selected_event_id = None
        self._edit_mode = EventEditMode.NONE
        self._refresh_table()
        self._refresh_controls()
        self._sync_range_notification()
        self._build_results_controls()
        self._request_events_refresh()

    def _add_event(self) -> None:
        """Publish add-event intent for current selection."""
        self.event_bus.publish(BeginAddAcqImageEventIntent(selection=self._copy_selection()))

    def _edit_event(self) -> None:
        """Publish edit-selected-event intent for current selection."""
        self.event_bus.publish(BeginEditAcqImageEventIntent(selection=self._copy_selection()))

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
        """Publish cancel add/edit intent."""
        self.event_bus.publish(CancelAddAcqImageEventIntent())

    def _set_events_visible(self, visible: bool) -> None:
        """Publish event visibility intent."""
        self.event_bus.publish(SetAcqImageEventsVisibleIntent(visible=visible))

    def _run_event_analysis(self) -> None:
        """Publish an explicit event reanalysis intent for current selection."""
        selection = self._copy_selection()
        if selection.file_id is None or selection.channel is None or selection.roi_id is None:
            ui.notify("Select a file, channel, and ROI before running event analysis.", type="warning")
            return
        try:
            detection_params = self._current_detection_params()
        except Exception as exc:
            ui.notify(f"Invalid event parameters: {exc}", type="negative")
            return
        self.event_bus.publish(
            RunAnalysisIntent(
                analysis_kind=AnalysisKind.EVENT,
                selection=selection,
                detection_params=detection_params,
            )
        )

    def _current_detection_params(self) -> dict[str, object]:
        """Return current event-analysis detection parameters.

        Returns:
            Detection parameter mapping.

        Raises:
            RuntimeError: If the event analysis class is unavailable.
        """
        cls = _load_event_analysis_class()
        if cls is None:
            raise RuntimeError("Event analysis plugin is not available")
        params = cls.get_default_detection_params()
        for name, control in self._param_controls.items():
            params[name] = control.value
        cls.validate_detection_params(params)
        return params

    def _build_param_controls(self) -> None:
        """Render editable event-analysis detection parameter controls."""
        if self._params_container is None:
            return
        self._params_container.clear()
        self._param_controls.clear()
        with self._params_container:
            cls = _load_event_analysis_class()
            if cls is None:
                ui.label("Event analysis plugin is not available.").classes("text-sm text-orange-600")
                return
            ui.label("Event parameters").classes("text-sm font-medium")
            defaults = cls.get_default_detection_params()
            for field in cls.get_detection_schema():
                if not field.visible:
                    continue
                label = field.display_name
                if field.unit:
                    label = f"{label} ({field.unit})"
                control = ui.number(label=label, value=defaults.get(field.name)).classes("w-full")
                if not field.editable:
                    control.props("readonly")
                if field.description:
                    control.tooltip(str(field.description))
                self._param_controls[field.name] = control

    def _build_results_controls(self) -> None:
        """Render compact event-analysis result status."""
        if self._results_container is None:
            return
        self._results_container.clear()
        acq_image = self.get_selected_acq_image()
        selection = self.current_selection
        with self._results_container:
            ui.label("Results").classes("text-sm font-medium")
            if acq_image is None:
                ui.label("No AcqImage selected.").classes("text-xs opacity-70")
                return
            if selection.channel is None or selection.roi_id is None:
                ui.label("Select a channel and ROI to inspect events.").classes("text-xs opacity-70")
                return
            parent_key = AnalysisKey(
                analysis_name=AnalysisKind.RADON_VELOCITY.value,
                channel=int(selection.channel),
                roi_id=int(selection.roi_id),
            )
            parent = acq_image.analysis_set.get(parent_key)
            if parent is None or parent.get_plot_data() is None:
                ui.label("Run Radon velocity analysis before creating or reanalyzing events.").classes("text-xs text-orange-600")
                return
            event_key = AnalysisKey(
                analysis_name=AnalysisKind.EVENT.value,
                channel=int(selection.channel),
                roi_id=int(selection.roi_id),
            )
            analysis = acq_image.analysis_set.get(event_key)
            if analysis is None:
                ui.label("No event analysis for this channel/ROI.").classes("text-xs opacity-70")
                return
            ui.label(f"Events: {len(getattr(analysis, 'get_events')())}").classes("text-xs opacity-70")

    def _on_analysis_completed(self, event: AnalysisCompleted) -> None:
        """Refresh results after relevant analysis completion.

        Args:
            event: Analysis completion event.
        """
        if event.analysis_kind not in (AnalysisKind.EVENT, AnalysisKind.RADON_VELOCITY):
            return
        if event.selection != self.current_selection:
            return
        self._build_results_controls()
        self._request_events_refresh()

    def _on_row_selected(self, row: dict[str, Any]) -> None:
        """Publish event selection from table row selection.

        Args:
            row: Selected table row.
        """
        if self._edit_mode is not EventEditMode.NONE:
            return
        event_id = int(row["event_id"])
        self.event_bus.publish(SelectAcqImageEventIntent(event_id=event_id))

    def _on_events_changed(self, event: AcqImageEventsChanged) -> None:
        """Refresh rows from event state when row data changed.

        Args:
            event: Events-changed state event.
        """
        if event.selection.file_id != self.current_selection.file_id:
            return
        if event.selection.channel != self.current_selection.channel:
            return
        if event.selection.roi_id != self.current_selection.roi_id:
            return
        new_rows = [dict(row) for row in event.rows]
        rows_changed = new_rows != self._rows
        self._rows = new_rows
        self._selected_event_id = event.selected_event_id
        self._events_visible = event.visible
        self._edit_mode = event.edit_mode
        if rows_changed:
            self._refresh_table()
        else:
            self._select_table_row()
        self._refresh_controls()
        self._sync_range_notification()

    def _on_selection_changed(self, event: AcqImageEventSelectionChanged) -> None:
        """Apply selected event id to table without replacing row data.

        Args:
            event: Selection state event.
        """
        self._selected_event_id = event.selected_event_id
        self._select_table_row()
        self._refresh_controls()


    def _sync_range_notification(self) -> None:
        """Show or dismiss the persistent add/edit instruction notification."""
        if self._edit_mode is EventEditMode.ADD:
            self._show_range_notification("Click and drag in the 2D plot to add an event.")
            return
        if self._edit_mode is EventEditMode.EDIT:
            self._show_range_notification("Click and drag in the 2D plot to update the selected event.")
            return
        self._dismiss_range_notification()

    def _show_range_notification(self, message: str) -> None:
        """Show a persistent instruction notification while waiting for x-range input.

        Args:
            message: Instruction text to display.
        """
        if self._range_notification is not None:
            if self._range_notification_message == message:
                return
            self._dismiss_range_notification()
        self._range_notification = ui.notification(
            message,
            type="info",
            timeout=0,
            close_button=False,
        )
        self._range_notification_message = message

    def _dismiss_range_notification(self) -> None:
        """Dismiss the persistent x-range instruction notification if present."""
        notification = self._range_notification
        self._range_notification = None
        self._range_notification_message = None
        if notification is None:
            return
        for method_name in ("dismiss", "close", "delete"):
            method = getattr(notification, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception:  # pragma: no cover - defensive UI cleanup
                    continue
                return

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
        if self._controls is None:
            return
        has_rows = bool(self._rows)
        has_selection = self._selected_event_id is not None
        is_editing = self._edit_mode is not EventEditMode.NONE
        self._controls.set_visible_checked(self._events_visible)
        self._controls.set_controls_state(
            has_rows=has_rows,
            has_selection=has_selection,
            is_editing=is_editing,
            can_run=self._can_run_event_analysis(),
        )

    def _can_run_event_analysis(self) -> bool:
        """Return whether current selection has required Radon parent analysis."""
        acq_image = self.get_selected_acq_image()
        selection = self.current_selection
        if acq_image is None or selection.channel is None or selection.roi_id is None:
            return False
        key = AnalysisKey(
            analysis_name=AnalysisKind.RADON_VELOCITY.value,
            channel=int(selection.channel),
            roi_id=int(selection.roi_id),
        )
        parent = acq_image.analysis_set.get(key)
        return parent is not None and parent.get_plot_data() is not None

    def _request_events_refresh(self) -> None:
        """Ask the controller to publish rows for the current selection."""
        self.event_bus.publish(RequestAcqImageEventsRefreshIntent(selection=self._copy_selection()))

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
        ColumnDef("event_mean", "Event mean", extra={"type": "numericColumn"}),
        ColumnDef("pre_mean", "Pre mean", extra={"type": "numericColumn"}),
        ColumnDef("post_mean", "Post mean", extra={"type": "numericColumn"}),
        ColumnDef("event_n", "Event n", extra={"type": "numericColumn"}),
        ColumnDef("pre_n", "Pre n", extra={"type": "numericColumn"}),
        ColumnDef("post_n", "Post n", extra={"type": "numericColumn"}),
    )
