"""CloudScope tree-view demo app.

Architecture mirrors the real cloudscope split:

* ``FakeAcqImage`` / ``FakeAcqImageList`` simulate ``src/acqstore/`` -- pure
  domain models. They know nothing about NiceGUI, tree mechanics, or
  ``row_id`` / ``hierarchy_path``. They expose their data via plain
  ``as_row_dict()``-style accessors.

* ``TreeView`` simulates a generic 2-level tree widget that would live in
  ``src/nicewidgets/``. It does not import or know about ``FakeAcqImage``;
  it only sees abstract rows with a unique id field and a hierarchy path
  field. The widget owns AG Grid composition, transactions, and event
  forwarding; its public callback emits the raw row ``dict`` (matching
  ``nicewidgets.table_widget.TableWidget.on_row_selected``).

* The ``@ui.page("/")`` block (the "intermediate" app, analogous to
  ``src/cloudscope/``) is the only layer that imports both. It owns the
  domain instance, defines column/auto-group presentation, builds row
  dicts from the domain via small adapter helpers, and handles row clicks.
"""

from __future__ import annotations

import datetime
from collections.abc import Callable, Mapping, Sequence
from enum import Enum
from typing import Any

from nicegui import ui

from nicewidgets.utils.logging import get_logger, setup_logging

setup_logging()
logger = get_logger("nicewidgets.demo_tree_app")

# Switch the AG Grid ESM bundle to the enterprise package so features like
# treeData / autoGroupColumnDef are available. NiceGUI 3.10.0 ships AG Grid
# 34.2.0; matching that version avoids API drift. set_module_source installs
# a GLOBAL import-map override, so it must run once at module import time
# before any ui.aggrid is created.
ui.aggrid.set_module_source(
    "https://cdn.jsdelivr.net/npm/ag-grid-enterprise@34.2.0/+esm"
)


# ------------------------------------------------------------------------------
# 1. DOMAIN MODELS (would live in src/acqstore/)
# ------------------------------------------------------------------------------


class AnalysisType(Enum):
    """Enumeration of analytical processing pathways the domain knows about."""

    DIAMETER = "diameter"
    VELOCITY = "velocity"
    SUM_INTENSITY = "sum intensity"


class FakeAcqImage:
    """Pure-Python domain model of an acquisition image on disk.

    Attributes are owned by the acqstore layer. No GUI / tree mechanics.
    """

    def __init__(
        self,
        file_path: str,
        name: str,
        channels: list[int],
        parent_folder: str,
        grandparent_folder: str,
        image_shape: tuple,
    ) -> None:
        """Initializes acquisition state.

        Args:
            file_path: Absolute filesystem path; the file's invariant identity.
            name: Short display name.
            channels: Imaging channel ids (e.g. ``[1, 2]``).
            parent_folder: Immediate parent directory name.
            grandparent_folder: Grandparent directory name.
            image_shape: Image dimensions tuple (e.g., ``(2048, 2048)``).
        """
        self.file_path: str = file_path
        self.name: str = name
        self.channels: list[int] = channels
        self.parent_folder: str = parent_folder
        self.grandparent_folder: str = grandparent_folder
        self.image_shape: str = str(image_shape)

        self.roi_ids: set[int] = set()
        # {(channel, roi_id, analysis_type_value): timestamp_str}
        self.analyses: dict[tuple[int, int, str], str] = {}

    def add_roi(self, roi_id: int) -> None:
        """Registers a new Region of Interest id on the file.

        Args:
            roi_id: Unique integer id for the region.
        """
        logger.info("registering ROI %s in '%s'", roi_id, self.name)
        self.roi_ids.add(roi_id)

    def run_analysis(self, channel: int, roi_id: int, analysis_type: AnalysisType) -> None:
        """Stamps an analysis result onto ``(channel, roi_id, analysis_type)``.

        Args:
            channel: Target channel id (must already exist on the file).
            roi_id: Target ROI id (must already exist on the file).
            analysis_type: Analysis type Enum value.
        """
        if channel not in self.channels or roi_id not in self.roi_ids:
            logger.warning("rejecting invalid channel/ROI pair: channel=%s roi_id=%s", channel, roi_id)
            return

        timestamp_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.analyses[(channel, roi_id, analysis_type.value)] = timestamp_str
        logger.info("computed '%s' for channel %s / ROI %s", analysis_type.value, channel, roi_id)

    def as_row_dict(self) -> dict[str, Any]:
        """Returns the file's own domain attributes as a flat dict.

        ``channels`` / ``rois`` are exposed as counts in this row
        representation. The internal attributes ``self.channels``
        (a ``list[int]``) and ``self.roi_ids`` (a ``set[int]``) are
        unrelated to these row fields.

        Returns:
            Mapping of public field names to values. Contains no tree-view
            mechanics (no ``row_id``, no ``hierarchy_path``).
        """
        return {
            "file_name": self.name,
            "parent_folder": self.parent_folder,
            "grandparent_folder": self.grandparent_folder,
            "image_shape": self.image_shape,
            "channels": len(self.channels),
            "rois": len(self.roi_ids),
        }


class FakeAcqImageList:
    """Pure-Python collection of acquisition files keyed by ``file_path``."""

    def __init__(self) -> None:
        """Initializes an empty collection."""
        self.files_map: dict[str, FakeAcqImage] = {}

    def insert_file(self, file_image: FakeAcqImage) -> None:
        """Inserts (or replaces) a file in the collection.

        Args:
            file_image: The domain object.
        """
        self.files_map[file_image.file_path] = file_image


# ------------------------------------------------------------------------------
# 2. GENERIC TREE WIDGET (would live in src/nicewidgets/)
# ------------------------------------------------------------------------------


class TreeView:
    """Generic 2-level AG Grid Enterprise tree widget.

    The widget is intentionally domain-agnostic. Rows are arbitrary mappings
    that must each contain:

    * a unique row id under ``row_id_field`` (default ``"row_id"``), and
    * a hierarchy path under ``path_field`` (default ``"hierarchy_path"``) --
      a list of ids whose length determines the row's tree depth.

    Public mutation API (covers the two flows the demo needs):

    * :meth:`replace_all_rows` -- full reset (e.g. on file-list change).
    * :meth:`replace_group_rows` -- replace all rows belonging to one
      top-level group id (the widget computes add/update/remove vs its
      internal known-ids state).

    Public selection API mirrors ``nicewidgets.table_widget.TableWidget``:
    callers supply an ``on_row_clicked`` callable that receives the raw row
    ``dict``.
    """

    def __init__(
        self,
        *,
        column_defs: Sequence[Mapping[str, Any]],
        initial_rows: Sequence[Mapping[str, Any]] = (),
        row_id_field: str = "row_id",
        path_field: str = "hierarchy_path",
        auto_group_column_def: Mapping[str, Any] | None = None,
        on_row_clicked: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        """Builds the AG Grid tree view inside the current NiceGUI slot.

        Args:
            column_defs: AG Grid column definitions (list of dicts).
            initial_rows: Initial rows. Each row must contain ``row_id_field``
                and ``path_field``.
            row_id_field: Name of the unique-id field on each row dict.
            path_field: Name of the hierarchy-path field on each row dict.
            auto_group_column_def: Optional AG Grid ``autoGroupColumnDef`` for
                the tree-group column.
            on_row_clicked: Optional callback fired with the raw row dict
                when the user clicks any row.
        """
        self._row_id_field = row_id_field
        self._path_field = path_field
        self._on_row_clicked = on_row_clicked

        # Tracks which row ids the grid currently holds, bucketed by their
        # top-level group id (i.e. hierarchy_path[0]). Required so
        # replace_group_rows can compute the "remove" bucket without
        # round-tripping to the grid.
        self._known_ids_by_group: dict[str, set[str]] = {}
        initial_list = [dict(r) for r in initial_rows]
        for row in initial_list:
            self._track_added(row)

        grid_options: dict[str, Any] = {
            "treeData": True,
            ":getDataPath": f"data => data.{path_field}",
            ":getRowId": f"params => params.data.{row_id_field}",
            "columnDefs": [dict(c) for c in column_defs],
            "rowData": initial_list,
        }
        if auto_group_column_def is not None:
            grid_options["autoGroupColumnDef"] = dict(auto_group_column_def)
        else:
            # No auto-group column requested: switch AG Grid to custom tree
            # display so it does NOT create its default "Group" column. The
            # caller is expected to host the disclosure triangles on one of
            # its own columns via ``cellRenderer: "agGroupCellRenderer"``.
            grid_options["groupDisplayType"] = "custom"

        logger.debug("composing TreeView with %d initial rows", len(initial_list))
        self._grid = ui.aggrid(
            options=grid_options,
            modules="enterprise",
        ).classes("w-full h-full min-w-0 min-h-0").style("height: 100%;")

        # AG Grid's rowClicked event carries cyclic references in its full
        # payload; NiceGUI docs document filtering to ['data'] (the row dict)
        # to avoid browser-side serialization failures.
        self._grid.on("rowClicked", self._handle_row_clicked, ["data"])

    def replace_all_rows(self, rows: Sequence[Mapping[str, Any]]) -> None:
        """Wipes the grid and replaces all rows.

        Args:
            rows: New full row set.
        """
        logger.info("replace_all_rows: %d rows", len(rows))
        rows_list = [dict(r) for r in rows]
        self._known_ids_by_group.clear()
        for row in rows_list:
            self._track_added(row)
        opts = dict(self._grid.options)
        opts["rowData"] = rows_list
        self._grid.options = opts
        self._grid.update()

    def replace_group_rows(self, group_id: str, rows: Sequence[Mapping[str, Any]]) -> None:
        """Replaces every row under a single top-level group via AG Grid transactions.

        The widget diffs ``rows`` against its known row ids for ``group_id``
        and dispatches a single ``applyTransaction({add, update, remove})``,
        then expands the group node so any newly added children are visible.

        Args:
            group_id: Top-level group id (the value of ``hierarchy_path[0]``
                shared by every row in this subtree).
            rows: The complete new set of rows for that group, including the
                group's own depth-1 row plus any depth-2 children.
        """
        rows_list = [dict(r) for r in rows]
        new_ids = {str(r[self._row_id_field]) for r in rows_list}
        old_ids = set(self._known_ids_by_group.get(group_id, set()))

        rows_to_add: list[dict[str, Any]] = []
        rows_to_update: list[dict[str, Any]] = []
        for row in rows_list:
            if str(row[self._row_id_field]) in old_ids:
                rows_to_update.append(row)
            else:
                rows_to_add.append(row)
        ids_to_remove = old_ids - new_ids

        transaction: dict[str, Any] = {}
        if rows_to_add:
            transaction["add"] = rows_to_add
        if rows_to_update:
            transaction["update"] = rows_to_update
        if ids_to_remove:
            transaction["remove"] = [{self._row_id_field: rid} for rid in ids_to_remove]
        if not transaction:
            return

        logger.info(
            "replace_group_rows[%s]: +%d / ~%d / -%d",
            group_id, len(rows_to_add), len(rows_to_update), len(ids_to_remove),
        )
        self._grid.run_grid_method("applyTransaction", transaction)
        self._known_ids_by_group[group_id] = new_ids
        self.expand_group(group_id)

    def expand_all_nodes(self) -> None:
        """Expands every tree group on the client."""
        logger.info("expand all")
        self._grid.run_grid_method("expandAll")

    def collapse_all_nodes(self) -> None:
        """Collapses every tree group on the client."""
        logger.info("collapse all")
        self._grid.run_grid_method("collapseAll")

    def expand_group(self, group_id: str) -> None:
        """Expands one tree group by id.

        Args:
            group_id: Row id of the depth-1 group row.
        """
        self._grid.run_row_method(group_id, "setExpanded", True)

    def _track_added(self, row: Mapping[str, Any]) -> None:
        """Records ``row`` in :attr:`_known_ids_by_group`."""
        path = row.get(self._path_field) or []
        if not path:
            return
        group_id = str(path[0])
        self._known_ids_by_group.setdefault(group_id, set()).add(str(row[self._row_id_field]))

    def _handle_row_clicked(self, e: Any) -> None:
        """Forwards AG Grid row-click events to the caller-supplied callback."""
        data: dict[str, Any] = (e.args or {}).get("data") or {}
        if not data:
            return
        if self._on_row_clicked is not None:
            self._on_row_clicked(dict(data))


# ------------------------------------------------------------------------------
# 3. APP / CONTROLLER (would live in src/cloudscope/)
# ------------------------------------------------------------------------------

# Field names + analysis-id encoding live here -- this layer owns the
# domain <-> tree-row contract.
_ROW_ID_FIELD = "row_id"
_PATH_FIELD = "hierarchy_path"


def _analysis_id(file: FakeAcqImage, channel: int, roi_id: int, analysis_type_value: str) -> str:
    """Builds a unique id string for an analysis row.

    Args:
        file: Owning file.
        channel: Analysis channel id.
        roi_id: Analysis ROI id.
        analysis_type_value: Analysis type's string value.

    Returns:
        Stable globally-unique id for the analysis row.
    """
    return f"{file.file_path}::ch_{channel}::roi_{roi_id}::type_{analysis_type_value}"


def _file_tree_row(file: FakeAcqImage) -> dict[str, Any]:
    """Composes the depth-1 tree row for a single file.

    Args:
        file: Domain file.

    Returns:
        Row dict with ``row_id``, ``hierarchy_path``, ``row_type`` plus the
        file's own domain attributes (from :meth:`FakeAcqImage.as_row_dict`).
    """
    return {
        _ROW_ID_FIELD: file.file_path,
        _PATH_FIELD: [file.file_path],
        "row_type": "File",
        "analysis_type": None,
        "analysis_time": None,
        **file.as_row_dict(),
    }


def _analysis_tree_row(
    file: FakeAcqImage,
    channel: int,
    roi_id: int,
    analysis_type_value: str,
    timestamp: str,
) -> dict[str, Any]:
    """Composes a depth-2 tree row for one analysis on a file.

    File-level columns are intentionally ``None`` on analysis rows so the
    parent file's facts are not repeated on each child cell.

    Args:
        file: Owning file.
        channel: Analysis channel id.
        roi_id: Analysis ROI id.
        analysis_type_value: Analysis type string value.
        timestamp: Timestamp produced by the domain when the analysis ran.

    Returns:
        Row dict suitable for :class:`TreeView`.
    """
    aid = _analysis_id(file, channel, roi_id, analysis_type_value)
    return {
        _ROW_ID_FIELD: aid,
        _PATH_FIELD: [file.file_path, aid],
        "row_type": "Analysis",
        "file_name": None,
        "parent_folder": None,
        "grandparent_folder": None,
        "image_shape": None,
        # On Analysis rows the unified Channels / ROIs columns carry the
        # single channel / ROI id of this analysis (rather than file-level
        # counts).
        "channels": channel,
        "rois": roi_id,
        "analysis_type": analysis_type_value,
        "analysis_time": timestamp,
    }


def _subtree_rows(file: FakeAcqImage) -> list[dict[str, Any]]:
    """Builds the full row set (parent + all analyses) for one file.

    Args:
        file: Domain file.

    Returns:
        List with the file's depth-1 row first, then a depth-2 row per analysis.
    """
    rows: list[dict[str, Any]] = [_file_tree_row(file)]
    for (channel, roi_id, analysis_type_value), timestamp in file.analyses.items():
        rows.append(_analysis_tree_row(file, channel, roi_id, analysis_type_value, timestamp))
    return rows


def _all_tree_rows(acq_list: FakeAcqImageList) -> list[dict[str, Any]]:
    """Builds the full tree row snapshot across every file in the domain.

    Args:
        acq_list: Domain collection.

    Returns:
        Flat list of tree row dicts.
    """
    rows: list[dict[str, Any]] = []
    for file in acq_list.files_map.values():
        rows.extend(_subtree_rows(file))
    return rows


def _column_defs() -> list[dict[str, Any]]:
    """Returns the AG Grid column definitions for the demo.

    The ``row_id`` column is part of the data contract (every row carries
    the unique id under this field) but is hidden in the demo via
    ``hide: True``. ``file_name`` hosts the tree disclosure triangles via
    AG Grid's ``agGroupCellRenderer`` so the otherwise-redundant
    auto-group column can be hidden (see :func:`_auto_group_column_def`).
    On Analysis rows the field is ``None`` so the cell renders blank
    (still indented as a tree child).
    """
    return [
        {"headerName": "Row Id", "field": "row_id", "hide": True},
        {
            "headerName": "File Name",
            "field": "file_name",
            "filter": "agTextColumnFilter",
            "cellRenderer": "agGroupCellRenderer",
            "cellRendererParams": {"suppressCount": True},
        },
        {"headerName": "Parent Folder", "field": "parent_folder", "filter": "agTextColumnFilter"},
        {"headerName": "Grandparent", "field": "grandparent_folder", "filter": "agTextColumnFilter"},
        {"headerName": "Shape", "field": "image_shape", "width": 120},
        # Hidden but still in the row dict so on_row_clicked can dispatch
        # on it (File vs Analysis).
        {"headerName": "Row Type", "field": "row_type", "hide": True},
        # Unified Channels / ROIs columns: counts on File rows, single
        # channel / ROI id on Analysis rows (the controller adapter sets
        # both shapes; see _file_tree_row and _analysis_tree_row).
        {"headerName": "Channels", "field": "channels", "width": 110},
        {"headerName": "ROIs", "field": "rois", "width": 110},
        {"headerName": "Analysis Type", "field": "analysis_type", "width": 140},
        {"headerName": "Analysis Time", "field": "analysis_time", "width": 160},
    ]


# Bootstrap mock repository dataset
acq_list = FakeAcqImageList()
acq_list.insert_file(
    FakeAcqImage("/data/exp_01/cell_matrix_A.raw", "cell_matrix_A.raw",
                 [1, 2], "exp_01", "data", (1024, 1024))
)
acq_list.insert_file(
    FakeAcqImage("/data/exp_01/sub_folder/cell_matrix_B.raw", "cell_matrix_B.raw",
                 [1], "sub_folder", "exp_01", (2048, 2048))
)


@ui.page("/")
def home() -> None:
    """Renders the demo page wiring domain + TreeView together."""
    with ui.column().classes("w-full p-6 max-w-7xl mx-auto gap-4"):

        with ui.row().classes("w-full items-center justify-between border-b pb-4"):
            with ui.column():
                ui.label("CloudScope Dynamic Tree Interface").classes("text-2xl font-bold text-slate-800")
                ui.label("Demo: domain (acqstore) + TreeView (nicewidgets) + app glue (cloudscope)").classes("text-sm text-slate-500")

            with ui.row().classes("gap-2"):
                ui.button("Expand All", on_click=lambda: tree.expand_all_nodes()).props("outline icon=unfold_more color=slate size=sm")
                ui.button("Collapse All", on_click=lambda: tree.collapse_all_nodes()).props("outline icon=unfold_less color=slate size=sm")

        def on_row_clicked(row_data: dict[str, Any]) -> None:
            """Logs whichever row the user clicks.

            The TreeView is domain-agnostic so it just hands us the row
            dict. This controller knows the schema and can route on the
            ``row_type`` field it inserted in ``_file_tree_row`` /
            ``_analysis_tree_row``.
            """
            if row_data.get("row_type") == "File":
                logger.info("file selected: row_id=%s", row_data.get(_ROW_ID_FIELD))
            else:
                logger.info(
                    "analysis selected: file=%s channel=%s roi=%s type=%s",
                    row_data.get(_PATH_FIELD, [None])[0],
                    row_data.get("channels"),
                    row_data.get("rois"),
                    row_data.get("analysis_type"),
                )

        with ui.column().classes("w-full min-w-0").style("height: 400px;"):
            tree = TreeView(
                column_defs=_column_defs(),
                initial_rows=_all_tree_rows(acq_list),
                row_id_field=_ROW_ID_FIELD,
                path_field=_PATH_FIELD,
                on_row_clicked=on_row_clicked,
            )

        with ui.card().classes("w-full p-4 bg-slate-50 border border-slate-200 mt-2"):
            ui.label("Mock Controller Actions Simulator").classes("text-sm font-bold text-slate-700 mb-2")

            with ui.row().classes("gap-3 items-center"):

                def trigger_add_roi() -> None:
                    logger.info("user created a new ROI coordinate")
                    target_file = acq_list.files_map["/data/exp_01/cell_matrix_A.raw"]
                    new_id: int = len(target_file.roi_ids) + 1

                    target_file.add_roi(new_id)
                    tree.replace_group_rows(target_file.file_path, _subtree_rows(target_file))
                    ui.notify(f"Added ROI {new_id} to cell_matrix_A.raw (Parent metrics updated)", type="info")

                ui.button("1. Add ROI (File A)", on_click=trigger_add_roi).props("color=teal size=sm icon=add_circle")

                def trigger_run_velocity() -> None:
                    logger.info("running velocity analysis routine")
                    target_file = acq_list.files_map["/data/exp_01/cell_matrix_A.raw"]

                    if not target_file.roi_ids:
                        ui.notify("Please add an ROI to File A first!", type="warning")
                        return

                    chosen_roi = sorted(target_file.roi_ids)[-1]
                    target_file.run_analysis(1, chosen_roi, AnalysisType.VELOCITY)
                    tree.replace_group_rows(target_file.file_path, _subtree_rows(target_file))
                    ui.notify(f"Computed Velocity for channel 1 / ROI {chosen_roi}!", type="positive")

                ui.button("2. Run Velocity Analysis", on_click=trigger_run_velocity).props("color=indigo size=sm icon=play_arrow")

                def trigger_run_intensity() -> None:
                    logger.info("running sum intensity analysis routine")
                    target_file = acq_list.files_map["/data/exp_01/cell_matrix_A.raw"]

                    if not target_file.roi_ids:
                        ui.notify("Please add an ROI to File A first!", type="warning")
                        return

                    chosen_roi = sorted(target_file.roi_ids)[-1]
                    target_file.run_analysis(2, chosen_roi, AnalysisType.SUM_INTENSITY)
                    tree.replace_group_rows(target_file.file_path, _subtree_rows(target_file))
                    ui.notify(f"Computed Intensity for channel 2 / ROI {chosen_roi}!", type="purple")

                ui.button("3. Run Intensity Analysis", on_click=trigger_run_intensity).props("color=purple size=sm icon=insights")

                # Action 4: Edit the timestamp of the most recently added analysis.
                # Re-runs the most recent (channel, roi, analysis_type) triple,
                # which overwrites its timestamp in the model. The TreeView's
                # replace_group_rows sees the row_id as known and routes it
                # through applyTransaction's "update" bucket.
                def trigger_edit_latest_analysis() -> None:
                    logger.info("updating timestamp on latest analysis")
                    target_file = acq_list.files_map["/data/exp_01/cell_matrix_A.raw"]

                    if not target_file.analyses:
                        ui.notify("No analyses on File A yet. Run one first!", type="warning")
                        return

                    last_key = next(reversed(target_file.analyses))
                    channel, roi_id, analysis_type_str = last_key
                    matched_type = next(at for at in AnalysisType if at.value == analysis_type_str)

                    target_file.run_analysis(channel, roi_id, matched_type)
                    tree.replace_group_rows(target_file.file_path, _subtree_rows(target_file))
                    ui.notify(f"Updated timestamp for ch {channel} / ROI {roi_id} / {analysis_type_str}", type="positive")

                ui.button("4. Update Latest Analysis Time", on_click=trigger_edit_latest_analysis).props("color=amber size=sm icon=edit")


ui.run(
    native=False,
    host='10.0.0.185',
    port=8080,
    # window_size=(1300, 780),
    title="CloudScope Tree Data Exploration Platform"
    )
