"""CloudScope file-list tree view backed by AcqStore tree-row APIs.

This view is a drop-in parallel to
:class:`cloudscope.views.file_list_view.AcqImageListTableView`. It uses
:class:`nicewidgets.tree_widget.tree_widget.TreeWidget` to display each
acquisition file with its analyses as child rows.

The legacy ``AcqImageListTableView`` is intentionally kept untouched.
Switching between table and tree presentation is a single-class swap at
the wiring site in :func:`cloudscope.pages.home_page.HomePage.build`.
"""

from __future__ import annotations

from typing import Any

from nicegui import ui

from acqstore.acq_image.tree_rows import (
    ACQ_TREE_ANALYSIS_CHANNEL_FIELD,
    ACQ_TREE_ANALYSIS_NAME_FIELD,
    ACQ_TREE_ANALYSIS_ROI_ID_FIELD,
    ACQ_TREE_PATH_FIELD,
    ACQ_TREE_ROW_ID_FIELD,
    ACQ_TREE_ROW_TYPE_ANALYSIS,
    ACQ_TREE_ROW_TYPE_FIELD,
    ACQ_TREE_ROW_TYPE_FILE,
    build_analysis_tree_row_id,
)
from acqstore.schema import ACQ_FILE_LIST_SCHEMA

from cloudscope.event_bus import EventBus
from cloudscope.events.acq_image_events import AcqImageEventsChanged
from cloudscope.events.analysis import AnalysisCompleted
from cloudscope.events.files import FileListChanged
from cloudscope.events.metadata import MetadataChanged
from cloudscope.events.roi import RoiChanged
from cloudscope.events.selection import SelectFileIntent
from cloudscope.schema_adapters import schema_to_column_defs
from cloudscope.utils.file_manager import reveal_in_file_manager
from cloudscope.utils.logging import get_logger
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.tree_widget.config import TreeWidgetConfig, scaled_row_header_heights_px
from nicewidgets.tree_widget.tree_widget import TreeWidget

logger = get_logger(__name__)


_TREE_CHEVRON_COLUMN_FIELD = "name"
"""Schema field that hosts the AG Grid disclosure chevron in the tree view.

Declared here, in the view, because chevron-column placement is a
display decision specific to this view. AcqStore populates the ``name``
schema field of every tree row (file name for file rows, analysis name
for analysis rows), so the chevron column shows a meaningful label at
both depths.
"""


class AcqImageListTreeView(BaseView):
    """File-list tree view for selecting AcqStore files and analyses.

    Parallel to :class:`AcqImageListTableView`. Differences:

    - Uses :class:`nicewidgets.tree_widget.tree_widget.TreeWidget` instead
      of ``TableWidget``.
    - Renders each file as a depth-1 row and each analysis as a depth-2
      child row, using ``AcqImage.get_tree_rows()`` and
      ``AcqImageList.get_tree_rows()`` from AcqStore.
    - On analysis-row click, publishes a fully-specified
      :class:`cloudscope.events.selection.SelectFileIntent` carrying
      ``(file_id, channel, roi_id, analysis_name)`` so the controller can
      restore the exact analysis row as the current selection.

    The view does not own the backend ``AcqImageList``. The page
    ``app_state`` is the source of truth for loaded files, and state
    events tell the view when to rebuild or patch the tree.

    Args:
        event_bus: CloudScope event bus used to publish selection intents
            and consume file-list/metadata/analysis/ROI state events.
        app_state: Optional home-page state used to refresh when shown and
            to resolve backend ``AcqImage`` objects for targeted subtree
            updates.
        table_font_size_px: Tree cell font size in pixels.
        initially_visible: Whether this view starts visible.
    """

    view_id = ViewId.FILE_LIST

    def __init__(
        self,
        event_bus: EventBus,
        *,
        app_state: Any | None = None,
        table_font_size_px: int = 12,
        initially_visible: bool = True,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self._table_font_size_px = int(table_font_size_px)
        self._tree: TreeWidget | None = None

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build and return the file-list tree UI.

        Args:
            parent: Optional NiceGUI parent element.

        Returns:
            Root NiceGUI element created by :class:`TreeWidget`.
        """
        font_px = int(self._table_font_size_px)
        row_h, header_h = scaled_row_header_heights_px(font_px)
        rows = self._read_tree_rows_from_state()
        self._tree = TreeWidget(
            columns=schema_to_column_defs(
                ACQ_FILE_LIST_SCHEMA,
                tree_group_display_field=_TREE_CHEVRON_COLUMN_FIELD,
            ),
            row_id_field=ACQ_TREE_ROW_ID_FIELD,
            rows=rows,
            on_row_selected=self._on_row_selected,
            on_build_context_menu=self._build_context_menu,
            config=TreeWidgetConfig(
                selection_mode="single",
                auto_size_columns=True,
                fit_columns_on_grid_resize=True,
                cell_font_size_px=font_px,
                row_height=row_h,
                header_height=header_h,
            ),
            path_field=ACQ_TREE_PATH_FIELD,
        )
        self.root = self._tree.build(parent=parent)
        self.after_build()
        return self.root

    def _build_context_menu(self, _tree: TreeWidget) -> None:
        """Add file-list-specific actions to the tree context menu.

        Args:
            _tree: Tree widget currently building its context menu. The
                argument is accepted to match the ``TreeWidget`` callback
                signature.

        Returns:
            None.
        """
        ui.menu_item("Reveal In Finder", on_click=self._reveal_selected_file_in_finder)

    def _reveal_selected_file_in_finder(self) -> None:
        """Reveal the selected file in the OS file manager.

        Resolves the parent file path from the selected row (whether the
        user picked a file row or an analysis child row) by reading the
        ``hierarchy_path`` field, whose first element is the file id.

        Returns:
            None.
        """
        if self._tree is None:
            logger.warning("Reveal In Finder requested before file tree was built")
            return

        selected_rows = self._tree.get_selected_rows()
        if not selected_rows:
            ui.notify("No file selected", type="warning")
            return

        selected_row = selected_rows[0]
        path = self._resolve_file_id_from_row(selected_row)
        if not isinstance(path, str) or not path:
            logger.warning("Selected tree row has no resolvable file path: %r", selected_row)
            ui.notify("Selected row has no file path", type="warning")
            return

        try:
            reveal_in_file_manager(path)
        except FileNotFoundError as exc:
            logger.warning("Unable to reveal missing file: %s", exc)
            ui.notify(f"File not found: {path}", type="warning")

    async def get_displayed_file_ids(self) -> list[str]:
        """Return file ids for files currently visible in the tree view.

        "Visible" means rendered by AG Grid after the user has applied
        filters and sorting. This method intentionally returns ONLY file
        rows (``tree_row_type == "file"``); analysis child rows are
        excluded even when expanded, because batch analysis consumes
        files, not analyses.

        The returned order matches the AG Grid view order at the time of
        call.

        Examples:
            - 5 files loaded, no filter, no sort:
              returns ``[file_id_1, ..., file_id_5]``.
            - User filters Genotype to "wt", 3 files match:
              returns ``[file_id_2, file_id_4, file_id_5]``.
            - User expands one file and clicks an analysis child:
              analysis rows are still excluded; returns parent file ids
              only.
            - Tree not built, or no files loaded: returns ``[]``.

        This is the authoritative source for CloudScope batch analysis
        file selection (``app_state.visible_file_ids_provider``).

        Returns:
            Ordered file identifiers for visible top-level rows.
        """
        if self._tree is None:
            return []
        rows = await self._tree.get_displayed_rows()
        file_ids: list[str] = []
        for row in rows:
            if row.get(ACQ_TREE_ROW_TYPE_FIELD) != ACQ_TREE_ROW_TYPE_FILE:
                continue
            value = row.get(ACQ_TREE_ROW_ID_FIELD)
            if isinstance(value, str) and value:
                file_ids.append(value)
        return file_ids

    def on_enabled_changed(self, enabled: bool) -> None:
        """Enable or disable tree interaction when the app busy state changes.

        Args:
            enabled: Desired enabled state.

        Returns:
            None.
        """
        if self._tree is not None:
            self._tree.set_enabled(enabled)

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
        """Refresh tree rows and selection from current app state.

        Reads tree rows directly from ``app_state.acq_image_list`` rather
        than trusting event payloads.

        Returns:
            None.
        """
        if self._tree is None:
            return
        self._tree.set_data(self._read_tree_rows_from_state())
        self._sync_table_selection()

    def _on_row_selected(self, row: dict[str, Any]) -> None:
        """Publish a selection intent from a clicked tree row.

        File-row clicks publish ``SelectFileIntent(file_id=...)`` so the
        controller resolves the file's default channel and ROI. Analysis-
        row clicks publish a fully-specified intent carrying
        ``(file_id, channel, roi_id, analysis_name)``.

        Args:
            row: Selected tree row dict.

        Returns:
            None.

        Raises:
            KeyError: If the row is missing required tree contract fields.
            TypeError: If row values have unexpected types.
        """
        row_type = row.get(ACQ_TREE_ROW_TYPE_FIELD)
        file_id = self._resolve_file_id_from_row(row)
        if not isinstance(file_id, str) or not file_id:
            raise TypeError(
                f"Selected tree row has no resolvable file_id: {row!r}"
            )

        if row_type == ACQ_TREE_ROW_TYPE_FILE:
            self.event_bus.publish(SelectFileIntent(file_id=file_id))
            return

        if row_type == ACQ_TREE_ROW_TYPE_ANALYSIS:
            channel = row.get(ACQ_TREE_ANALYSIS_CHANNEL_FIELD)
            roi_id = row.get(ACQ_TREE_ANALYSIS_ROI_ID_FIELD)
            analysis_name = row.get(ACQ_TREE_ANALYSIS_NAME_FIELD)
            if not isinstance(channel, int) or not isinstance(roi_id, int):
                raise TypeError(
                    "Analysis tree row is missing channel/roi_id ints: "
                    f"{row!r}"
                )
            if not isinstance(analysis_name, str) or not analysis_name:
                raise TypeError(
                    f"Analysis tree row is missing analysis_name: {row!r}"
                )
            self.event_bus.publish(
                SelectFileIntent(
                    file_id=file_id,
                    channel=channel,
                    roi_id=roi_id,
                    analysis_name=analysis_name,
                )
            )
            return

        raise KeyError(f"Unknown tree row type: {row_type!r}")

    def on_primary_selection_changed(self) -> None:
        """Reflect cached primary selection in the tree selection.

        Returns:
            None.
        """
        self._sync_table_selection()

    def _sync_table_selection(self) -> None:
        """Apply cached primary selection to the tree widget.

        When ``current_selection.analysis_name`` is set, this selects the
        matching analysis child row by its stable tree row id; otherwise
        it selects the parent file row.

        Returns:
            None.
        """
        if self._tree is None:
            return
        file_id = self.current_selection.file_id
        if file_id is None:
            self._tree.clear_selection()
            return

        analysis_name = self.current_selection.analysis_name
        channel = self.current_selection.channel
        roi_id = self.current_selection.roi_id
        if (
            analysis_name is not None
            and isinstance(channel, int)
            and isinstance(roi_id, int)
        ):
            row_id = build_analysis_tree_row_id(
                file_id,
                analysis_name,
                channel,
                roi_id,
            )
            self._tree.set_selected_row_ids([row_id], origin="state")
            return

        self._tree.set_selected_row_ids([file_id], origin="state")

    def _on_metadata_changed(self, event: MetadataChanged) -> None:
        """Refresh one file's subtree after metadata apply.

        Ignores ``event.file_list_row`` (flat schema row, only meaningful
        to the legacy table view) and rebuilds the subtree from the
        backend ``AcqImage`` instead.

        Args:
            event: Metadata changed event.

        Returns:
            None.
        """
        if self._tree is None:
            return
        self._replace_group_rows_from_acq_image(event.file_id)

    def _on_file_list_changed(self, event: FileListChanged) -> None:
        """Rebuild the tree when controller publishes a new file list.

        Ignores ``event.rows`` (flat schema rows, only meaningful to the
        legacy table view) and rebuilds from ``app_state.acq_image_list``.

        Args:
            event: File-list changed state event.

        Returns:
            None.
        """
        if self._tree is None:
            return
        _ = event  # legacy-shaped payload intentionally unused
        self._tree.set_data(self._read_tree_rows_from_state())
        self._sync_table_selection()

    def _on_analysis_completed(self, event: AnalysisCompleted) -> None:
        """Refresh one file's subtree after analysis completes.

        The tree view treats ``AcqImage`` as the source of truth and
        refreshes whenever ``file_id`` is set, regardless of
        ``event.success``. Rationale: batch analyses publish per-file
        :class:`AnalysisCompleted` events whose ``success`` flag is the
        AND of the batch's aggregate success and the per-file outcome,
        so a single failed file in a batch would otherwise suppress the
        tree refresh for all successful files in the same batch. The
        backing ``AcqImage`` already reflects the actual ROI / analysis
        state, so rebuilding the subtree from it is always correct.

        Args:
            event: Analysis completion event.

        Returns:
            None.
        """
        file_id = event.selection.file_id
        if file_id is None:
            return
        self._replace_group_rows_from_acq_image(file_id)

    def _on_acq_image_events_changed(self, event: AcqImageEventsChanged) -> None:
        """Refresh one file's subtree after AcqImage event-analysis changes.

        Args:
            event: AcqImage events changed state event.

        Returns:
            None.
        """
        file_id = event.selection.file_id
        if file_id is None:
            return
        self._replace_group_rows_from_acq_image(file_id)

    def _on_roi_changed(self, event: RoiChanged) -> None:
        """Refresh one file's subtree after ROI model changes.

        Args:
            event: ROI changed state event.

        Returns:
            None.
        """
        file_id = event.selection.file_id
        if file_id is None:
            return
        self._replace_group_rows_from_acq_image(file_id)

    def _replace_group_rows_from_acq_image(self, file_id: str) -> None:
        """Replace one file's full subtree from the current ``AcqImage``.

        Replacing the subtree via AG Grid ``applyTransaction`` drops
        client-side selection state for rows in the affected group, even
        when their stable row id is unchanged. To keep analysis-row
        selection visually persistent across analysis runs, this method
        re-applies :meth:`_sync_table_selection` after the replace when
        the cached selection points at the same file.

        Args:
            file_id: Stable acquisition file identifier.

        Returns:
            None.
        """
        if self._tree is None:
            logger.error("tree not found")
            return
        acq_image = self.get_acq_image_by_file_id(file_id)
        if acq_image is None:
            logger.error("acq_image not found: %s", file_id)
            return
        self._tree.replace_group_rows(file_id, acq_image.get_tree_rows())
        if self.current_selection.file_id == file_id:
            self._sync_table_selection()

    def _read_tree_rows_from_state(self) -> list[dict[str, Any]]:
        """Read tree rows for the entire current file list.

        Returns:
            Tree row dicts from ``AcqImageList.get_tree_rows()`` in
            display order. Empty list when no list is loaded.
        """
        acq_image_list = self.get_acq_image_list()
        if acq_image_list is None:
            return []
        return acq_image_list.get_tree_rows()

    @staticmethod
    def _resolve_file_id_from_row(row: dict[str, Any]) -> str | None:
        """Return the parent file id for either a file or analysis row.

        Uses ``hierarchy_path[0]`` (always the file id by AcqStore tree
        contract) so this works uniformly for both row types.

        Args:
            row: Tree row dict.

        Returns:
            File id string, or ``None`` if the row has no resolvable
            hierarchy path.
        """
        path = row.get(ACQ_TREE_PATH_FIELD)
        if isinstance(path, (list, tuple)) and path:
            head = path[0]
            return str(head) if head is not None else None
        return None
