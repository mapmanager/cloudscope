"""CloudScope file-list table view backed by AcqStore and NiceWidgets."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from acqstore.acq_image.acq_image_list import AcqImageList
from acqstore.schema import ACQ_FILE_LIST_SCHEMA
from cloudscope.app_config import AppConfig
from cloudscope.event_bus import EventBus
from cloudscope.events import FileListChanged, MetadataChanged, SelectFileIntent
from cloudscope.schema_adapters import schema_to_column_defs
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.table_widget.config import TableWidgetConfig, scaled_row_header_heights_px
from nicewidgets.table_widget.table_widget import TableWidget


class AcqImageListTableView(BaseView):
    """File-list table view for selecting AcqStore files.

    Args:
        event_bus: CloudScope event bus used to publish file-selection intents
            and consume file-selection state events while visible.
        acq_image_list: Backend file list to display.
        app_config: Persisted GUI config.
        app_state: Optional home-page state used to refresh when shown.
        row_id_field: Row field used as the stable table row identifier.
        initially_visible: Whether this view starts visible.
    """

    view_id = ViewId.FILE_LIST

    def __init__(
        self,
        event_bus: EventBus,
        acq_image_list: AcqImageList | None = None,
        *,
        app_config: AppConfig,
        app_state: Any | None = None,
        row_id_field: str = "path",
        initially_visible: bool = True,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self._acq_image_list = acq_image_list
        self._app_config = app_config
        self._row_id_field = row_id_field
        self._table: TableWidget | None = None

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build and return the file-list table UI.

        Args:
            parent: Optional NiceGUI parent element.

        Returns:
            Root NiceGUI element created by ``TableWidget``.
        """
        font_px = int(self._app_config.data.table_font_size_px)
        row_h, header_h = scaled_row_header_heights_px(font_px)
        self._table = TableWidget(
            columns=schema_to_column_defs(ACQ_FILE_LIST_SCHEMA),
            row_id_field=self._row_id_field,
            rows=self._acq_image_list.get_schema_rows() if self._acq_image_list is not None else [],
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

    def subscribe_events(self) -> None:
        """Subscribe to file-list events while visible.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(FileListChanged, self._on_file_list_changed))
        self.add_subscription(self.event_bus.subscribe(MetadataChanged, self._on_metadata_changed))

    def refresh_from_state(self) -> None:
        """Refresh table rows and selection from current app state.

        Returns:
            None.
        """
        if self.app_state is None or self._table is None:
            return
        acq_image_list = getattr(self.app_state, "acq_image_list", None)
        if acq_image_list is not None:
            self._acq_image_list = acq_image_list
            self._table.set_data(acq_image_list.get_schema_rows())
        selection = getattr(self.app_state, "selection", None)
        file_id = getattr(selection, "file_id", None)
        if file_id is None:
            self._table.clear_selection()
        else:
            self._table.set_selected_row_ids([file_id], origin="state")

    def set_data(self, acq_image_list: AcqImageList) -> None:
        """Replace the displayed backend file list.

        Args:
            acq_image_list: New backend file list.

        Returns:
            None.

        Raises:
            RuntimeError: If the table has not been built.
        """
        if self._table is None:
            raise RuntimeError("AcqImageListTableView.set_data() called before build()")
        self._acq_image_list = acq_image_list
        self._table.set_data(acq_image_list.get_schema_rows())

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
