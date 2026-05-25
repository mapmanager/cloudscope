"""CloudScope file-list table view backed by AcqStore and NiceWidgets."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from acqstore.schema import ACQ_FILE_LIST_SCHEMA
from cloudscope.event_bus import EventBus
from cloudscope.events.acq_image_events import AcqImageEventsChanged
from cloudscope.events.analysis import AnalysisCompleted
from cloudscope.events.files import FileListChanged
from cloudscope.events.metadata import MetadataChanged
from cloudscope.events.roi import RoiChanged
from cloudscope.events.selection import SelectFileIntent
from cloudscope.schema_adapters import schema_to_column_defs
from cloudscope.utils.logging import get_logger
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.table_widget.config import TableWidgetConfig, scaled_row_header_heights_px
from nicewidgets.table_widget.table_widget import TableWidget

logger = get_logger(__name__)


class AcqImageListTableView(BaseView):
    """File-list table view for selecting AcqStore files.

    The view does not own the backend ``AcqImageList``. The page ``app_state``
    is the source of truth for loaded files, and state events tell the view when
    to redraw or patch rows.

    Args:
        event_bus: CloudScope event bus used to publish file-selection intents
            and consume file-list state events while visible.
        app_state: Optional home-page state used to refresh when shown and to
            resolve backend ``AcqImage`` objects for targeted row updates.
        table_font_size_px: Table cell font size in pixels.
        row_id_field: Row field used as the stable table row identifier.
        initially_visible: Whether this view starts visible.
    """

    view_id = ViewId.FILE_LIST

    def __init__(
        self,
        event_bus: EventBus,
        *,
        app_state: Any | None = None,
        table_font_size_px: int = 12,
        row_id_field: str = "path",
        initially_visible: bool = True,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self._table_font_size_px = int(table_font_size_px)
        self._row_id_field = row_id_field
        self._table: TableWidget | None = None

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build and return the file-list table UI.

        Args:
            parent: Optional NiceGUI parent element.

        Returns:
            Root NiceGUI element created by ``TableWidget``.
        """
        font_px = int(self._table_font_size_px)
        row_h, header_h = scaled_row_header_heights_px(font_px)
        acq_image_list = self.get_acq_image_list()
        rows = acq_image_list.get_schema_rows() if acq_image_list is not None else []
        self._table = TableWidget(
            columns=schema_to_column_defs(ACQ_FILE_LIST_SCHEMA),
            row_id_field=self._row_id_field,
            rows=rows,
            on_row_selected=self._on_row_selected,
            config=TableWidgetConfig(
                selection_mode="single",
                auto_size_columns=True,
                cell_font_size_px=font_px,
                row_height=row_h,
                header_height=header_h,
            ),
        )
        self.root = self._table.build(parent=parent)
        self.after_build()
        return self.root

    def on_enabled_changed(self, enabled: bool) -> None:
        """Enable or disable table interaction when the app busy state changes.

        Args:
            enabled: Desired enabled state.

        Returns:
            None.
        """
        if self._table is not None:
            self._table.set_enabled(enabled)

    def subscribe_events(self) -> None:
        """Subscribe to file-list events while visible.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(FileListChanged, self._on_file_list_changed))
        self.add_subscription(self.event_bus.subscribe(MetadataChanged, self._on_metadata_changed))
        self.add_subscription(self.event_bus.subscribe(AnalysisCompleted, self._on_analysis_completed))
        self.add_subscription(self.event_bus.subscribe(AcqImageEventsChanged, self._on_acq_image_events_changed))
        self.add_subscription(self.event_bus.subscribe(RoiChanged, self._on_roi_changed))

    def refresh_from_state(self) -> None:
        """Refresh table rows and selection from current app state.

        Returns:
            None.
        """
        if self._table is None:
            return
        acq_image_list = self.get_acq_image_list()
        if acq_image_list is not None:
            self._table.set_data(acq_image_list.get_schema_rows())
        self._sync_table_selection()

    def _on_row_selected(self, row: dict[str, Any]) -> None:
        """Publish a file-selection intent from a selected table row.

        Args:
            row: Selected table row.

        Returns:
            None.

        Raises:
            KeyError: If the configured row identifier is missing.
            TypeError: If the configured row identifier value is not a string.
        """
        file_id = row[self._row_id_field]
        if not isinstance(file_id, str):
            raise TypeError(
                f"Expected file_id at {self._row_id_field!r} to be str, "
                f"got {type(file_id).__name__}"
            )
        self.event_bus.publish(SelectFileIntent(file_id=file_id))

    def on_primary_selection_changed(self) -> None:
        """Reflect cached primary selection in the table selection.

        Returns:
            None.
        """
        self._sync_table_selection()

    def _sync_table_selection(self) -> None:
        """Apply cached primary file selection to the table widget.

        Returns:
            None.
        """
        if self._table is None:
            return
        file_id = self.current_selection.file_id
        if file_id is None:
            self._table.clear_selection()
            return
        self._table.set_selected_row_ids([file_id], origin="state")

    def _on_metadata_changed(self, event: MetadataChanged) -> None:
        """Refresh one table row after metadata apply.

        Args:
            event: Metadata changed event containing an updated file-list row.

        Returns:
            None.
        """
        if self._table is None:
            return
        self._table.update_row(event.file_id, dict(event.file_list_row))

    def _on_file_list_changed(self, event: FileListChanged) -> None:
        """Replace table rows when controller publishes a new file list.

        Args:
            event: File-list changed state event.

        Returns:
            None.
        """
        if self._table is None:
            return
        self._table.set_data(list(event.rows))
        self._sync_table_selection()

    def _on_analysis_completed(self, event: AnalysisCompleted) -> None:
        """Refresh one table row after analysis completes.

        Args:
            event: Analysis completion event containing the analyzed selection.

        Returns:
            None.
        """
        if not event.success:
            return
        file_id = event.selection.file_id
        if file_id is None:
            return
        self._update_row_from_acq_image(file_id)


    def _on_acq_image_events_changed(self, event: AcqImageEventsChanged) -> None:
        """Refresh one table row after AcqImage event analysis changes.

        Event analysis mutations make the owning ``AcqImage`` dirty, but they do
        not rebuild the file list. This targeted patch keeps the table's dirty
        indicator in sync without replacing all rows or changing selection.

        Args:
            event: AcqImage events changed state event.

        Returns:
            None.
        """
        file_id = event.selection.file_id
        if file_id is None:
            return
        self._update_row_from_acq_image(file_id)

    def _on_roi_changed(self, event: RoiChanged) -> None:
        """Refresh one table row after ROI model changes.

        Args:
            event: ROI changed state event containing the affected file.

        Returns:
            None.
        """
        file_id = event.selection.file_id
        if file_id is None:
            return
        self._update_row_from_acq_image(file_id)

    def _update_row_from_acq_image(self, file_id: str) -> None:
        """Refresh one table row from the current AcqImageList.

        Args:
            file_id: Stable acquisition file identifier.

        Returns:
            None.
        """
        if self._table is None:
            logger.error("table not found")
            return
        acq_image = self.get_acq_image_by_file_id(file_id)
        if acq_image is None:
            logger.error("acq_image not found: %s", file_id)
            return
        self._table.update_row(file_id, acq_image.get_schema_row())
