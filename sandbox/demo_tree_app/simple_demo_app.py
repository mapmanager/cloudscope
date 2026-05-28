"""Minimal enterprise AG Grid demo.

This file exists to verify that an enterprise ``ui.aggrid`` actually renders
in NiceGUI 3.10.0. It deliberately avoids tree data, custom renderers, and any
JS callbacks beyond ``getRowId`` so that any rendering problem is easy to spot.

Key practices applied (compared to ``demo_tree_app.py``):
  * JS-valued grid options use NiceGUI's ``:``-prefixed keys (e.g. ``:getRowId``)
    rather than ``"js:..."`` string values, which NiceGUI does not interpret.
  * The grid is mounted inside a parent container with an explicit pixel height
    so AG Grid has a real box to render into.
  * ``modules="enterprise"`` is passed as a keyword argument matching the
    NiceGUI 3.10 ``ui.aggrid`` signature.
"""

from typing import Any

from nicegui import ui

ui.aggrid.set_module_source(
    "https://cdn.jsdelivr.net/npm/ag-grid-enterprise@34.2.0/+esm"
)

def build_rows() -> list[dict[str, Any]]:
    """Return a small flat row dataset for the grid.

    Returns:
        List of plain dicts; each dict is one AG Grid row.
    """
    return [
        {"row_key": "A", "file_name": "cell_matrix_A.raw", "channels": 2, "shape": "1024x1024"},
        {"row_key": "B", "file_name": "cell_matrix_B.raw", "channels": 1, "shape": "2048x2048"},
        {"row_key": "C", "file_name": "cell_matrix_C.raw", "channels": 3, "shape": "512x512"},
    ]


def build_grid_options() -> dict[str, Any]:
    """Return AG Grid options for a minimal enterprise grid.

    Returns:
        Options dict suitable for ``ui.aggrid(options=...)``.
    """
    return {
        "columnDefs": [
            {"headerName": "File", "field": "file_name", "filter": "agTextColumnFilter"},
            {"headerName": "Channels", "field": "channels", "width": 130},
            {"headerName": "Shape", "field": "shape", "width": 160},
        ],
        "defaultColDef": {
            "sortable": True,
            "filter": True,
            "resizable": True,
        },
        "rowData": build_rows(),
        ":getRowId": "params => params.data.row_key",
    }


@ui.page("/")
def home() -> None:
    """Render a single enterprise AG Grid inside a sized container."""
    with ui.column().classes("w-full p-6 max-w-5xl mx-auto gap-4"):
        ui.label("Simple Enterprise AG Grid Demo").classes("text-2xl font-bold text-slate-800")
        ui.label("Minimal flat data to confirm the grid renders.").classes("text-sm text-slate-500")

        with ui.column().classes("w-full min-w-0").style("height: 480px;"):
            ui.aggrid(
                options=build_grid_options(),
                modules="enterprise",
            ).classes("w-full h-full min-w-0 min-h-0").style("height: 100%;")


ui.run(native=True, window_size=(1100, 800), title="Simple Enterprise AG Grid")
