"""CloudScope tree-view demo app.

Architecture mirrors the real cloudscope split:

* ``FakeAcqImage`` / ``FakeAcqImageList`` simulate ``src/acqstore/`` -- pure
  domain models. They know nothing about NiceGUI, tree mechanics, or
  ``row_id`` / ``hierarchy_path``. They expose their data via plain
  ``as_row_dict()``-style accessors.

* ``TreeWidget`` simulates a generic 2-level tree widget that would live in
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
from enum import Enum
from typing import Any

from nicegui import ui

from nicewidgets.aggrid_common.column_def import ColumnDef
from nicewidgets.tree_widget.tree_widget import TreeWidget
from nicewidgets.utils.logging import get_logger, setup_logging

setup_logging()
logger = get_logger("nicewidgets.demo_tree_app")

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
# 2. APP / CONTROLLER (would live in src/cloudscope/)
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
        Row dict suitable for :class:`TreeWidget`.
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


def _columns() -> list[ColumnDef]:
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
        ColumnDef(field='row_id', headerName='Row Id', hide=True),
        ColumnDef(
            field='file_name',
            headerName='File Name',
            extra={
                'filter': 'agTextColumnFilter',
                'cellRenderer': 'agGroupCellRenderer',
                'cellRendererParams': {'suppressCount': True},
            },
        ),
        ColumnDef(field='parent_folder', headerName='Parent Folder', extra={'filter': 'agTextColumnFilter'}),
        ColumnDef(field='grandparent_folder', headerName='Grandparent', extra={'filter': 'agTextColumnFilter'}),
        ColumnDef(field='image_shape', headerName='Shape', extra={'width': 120}),
        # Hidden but still in the row dict so on_row_clicked can dispatch
        # on it (File vs Analysis).
        ColumnDef(field='row_type', headerName='Row Type', hide=True),
        # Unified Channels / ROIs columns: counts on File rows, single
        # channel / ROI id on Analysis rows (the controller adapter sets
        # both shapes; see _file_tree_row and _analysis_tree_row).
        ColumnDef(field='channels', headerName='Channels', extra={'width': 110}),
        ColumnDef(field='rois', headerName='ROIs', extra={'width': 110}),
        ColumnDef(field='analysis_type', headerName='Analysis Type', extra={'width': 140}),
        ColumnDef(field='analysis_time', headerName='Analysis Time', extra={'width': 160}),
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
    """Renders the demo page wiring domain + TreeWidget together."""
    with ui.column().classes("w-full p-6 max-w-7xl mx-auto gap-4"):

        with ui.row().classes("w-full items-center justify-between border-b pb-4"):
            with ui.column():
                ui.label("CloudScope Dynamic Tree Interface").classes("text-2xl font-bold text-slate-800")
                ui.label("Demo: domain (acqstore) + TreeWidget (nicewidgets) + app glue (cloudscope)").classes("text-sm text-slate-500")

            with ui.row().classes("gap-2"):
                ui.button("Expand All", on_click=lambda: tree.expand_all_nodes()).props("outline icon=unfold_more color=slate size=sm")
                ui.button("Collapse All", on_click=lambda: tree.collapse_all_nodes()).props("outline icon=unfold_less color=slate size=sm")

        def on_row_selected(row_data: dict[str, Any]) -> None:
            """Logs whichever row the user clicks.

            The TreeWidget is domain-agnostic so it just hands us the row
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
            tree = TreeWidget(
                columns=_columns(),
                rows=_all_tree_rows(acq_list),
                row_id_field=_ROW_ID_FIELD,
                path_field=_PATH_FIELD,
                on_row_selected=on_row_selected,
            )
            tree.build()

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
                # which overwrites its timestamp in the model. The TreeWidget's
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
    native=True,
    # native=False,
    # host='10.0.0.185',
    # port=8080,
    window_size=(1300, 780),
    title="CloudScope Tree Data Exploration Platform"
    )
