"""CloudScope file-list table view backed by AcqStore and NiceWidgets."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from acqstore.acq_image.acq_image_list import AcqImageList
from acqstore.schema import ACQ_FILE_LIST_SCHEMA
from cloudscope.core.event_bus import EventBus
from cloudscope.core.events import FileListChanged, FileSelectionChanged, MetadataChanged, SelectFileIntent
from cloudscope.gui.schema_adapters import schema_to_column_defs
from nicewidgets.table_widget.config import TableWidgetConfig
from nicewidgets.table_widget.table_widget import TableWidget


# DEFAULT_ACQ_IMAGE_FOLDER = "/Users/cudmore/Sites/cloudscope/tests/acqstore/data/oir-samples"


class AcqImageListTableView:
    """File-list table view for selecting AcqStore files.

    Args:
        event_bus: CloudScope event bus used to publish file-selection intents
            and consume file-selection state events.
        acq_image_list: Backend file list to display.
        row_id_field: Row field used as the stable table row identifier. For
            current AcqStore rows, this should remain ``"path"`` because
            ``AcqImage.file_id`` is the absolute path.
    """

    def __init__(
        self,
        event_bus: EventBus,
        acq_image_list: AcqImageList | None = None,
        *,
        row_id_field: str = "path",
    ) -> None:
        self._event_bus = event_bus
        self._acq_image_list = acq_image_list
        self._row_id_field = row_id_field
        self._table: TableWidget | None = None

        self._event_bus.subscribe(FileSelectionChanged, self._on_file_selection_changed)
        self._event_bus.subscribe(FileListChanged, self._on_file_list_changed)
        self._event_bus.subscribe(MetadataChanged, self._on_metadata_changed)

    def build(self, parent: ui.element | None = None) -> ui.column:
        """Build and return the file-list table UI.

        Args:
            parent: Optional NiceGUI parent element. If omitted, the widget is
                built in the current slot.

        Returns:
            Root NiceGUI column element created by ``TableWidget``.
        """
        self._table = TableWidget(
            columns=schema_to_column_defs(ACQ_FILE_LIST_SCHEMA),
            row_id_field=self._row_id_field,
            rows=self._acq_image_list.get_schema_rows() if self._acq_image_list is not None else [],
            on_row_selected=self._on_row_selected,
            config=TableWidgetConfig(
                selection_mode="single",
                auto_size_columns=True,
            ),
        )
        return self._table.build(parent=parent)

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
            KeyError: If the configured row identifier is missing from the row.
            TypeError: If the configured row identifier value is not a string.
        """
        file_id = row[self._row_id_field]
        if not isinstance(file_id, str):
            raise TypeError(
                f"Expected file_id at {self._row_id_field!r} to be str, "
                f"got {type(file_id).__name__}"
            )
        self._event_bus.publish(SelectFileIntent(file_id=file_id))

    def _on_file_selection_changed(self, event: FileSelectionChanged) -> None:
        """Reflect controller file selection in the table selection.

        Args:
            event: Current file selection state.

        Returns:
            None.
        """
        if self._table is None:
            return

        if event.file_id is None:
            self._table.clear_selection()
            return

        self._table.set_selected_row_ids([event.file_id], origin="state")

    def _on_metadata_changed(self, event: MetadataChanged) -> None:
        """Refresh one table row after metadata apply (row keys match file-list schema)."""
        if self._table is None:
            return
        self._table.update_row(event.file_id, dict(event.row))

    def _on_file_list_changed(self, event: FileListChanged) -> None:
        """Replace table rows when controller publishes a new file list."""
        if self._table is None:
            return
        self._table.set_data(list(event.rows))
