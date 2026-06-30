"""Tests for NicePool X/Y column picker AG Grid options."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from nicewidgets.nicepool.plot_state import PlotState
from nicewidgets.nicepool.pool_control_panel import PoolControlPanel


def _panel(df: pd.DataFrame) -> PoolControlPanel:
    return PoolControlPanel(
        df,
        layout="1x1",
        current_plot_index=0,
        initial_state=PlotState(
            pre_filter={},
            xcol=str(df.columns[0]),
            ycol=str(df.columns[0]),
        ),
        on_any_change=MagicMock(),
        on_layout_change=MagicMock(),
        on_save_config=MagicMock(),
        on_plot_radio_change=MagicMock(),
        on_apply_current_to_others=MagicMock(),
        on_replot_current=MagicMock(),
        on_reset_to_default=MagicMock(),
        on_copy_stats=MagicMock(),
        on_copy_full_table=MagicMock(),
        on_x_column_selected=MagicMock(),
        on_y_column_selected=MagicMock(),
        show_plot_presets=False,
    )


def test_column_picker_aggrid_includes_index_and_disables_column_drag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """X/Y column pickers should show 1-based indices and lock column order."""
    columns = [f"col_{i}" for i in range(1, 103)]
    df = pd.DataFrame({name: [float(i)] for i, name in enumerate(columns, start=1)})
    panel = _panel(df)

    captured: list[dict[str, Any]] = []

    class _FakeAggrid:
        def __init__(self, options: dict[str, Any]) -> None:
            self.options = options
            captured.append(options)

        def classes(self, *_args: object, **_kwargs: object) -> _FakeAggrid:
            return self

        def style(self, *_args: object, **_kwargs: object) -> _FakeAggrid:
            return self

        def on(self, *_args: object, **_kwargs: object) -> None:
            return None

    monkeypatch.setattr(
        "nicewidgets.nicepool.pool_control_panel._ensure_aggrid_compact_css",
        lambda: None,
    )
    monkeypatch.setattr(
        "nicewidgets.nicepool.pool_control_panel.ui.aggrid",
        _FakeAggrid,
    )
    monkeypatch.setattr(
        "nicewidgets.nicepool.pool_control_panel.ui.timer",
        lambda *_args, **_kwargs: MagicMock(),
    )

    panel._create_column_aggrid("X column", str(df.columns[0]), MagicMock())

    assert len(captured) == 1
    opts = captured[0]
    assert opts["suppressMovableColumns"] is True
    assert opts[":getRowId"] == "(params) => String(params.data.column)"

    row_data = opts["rowData"]
    assert len(row_data) == 102
    assert row_data[0] == {"index": 1, "column": "col_1"}
    assert row_data[99] == {"index": 100, "column": "col_100"}
    assert row_data[-1] == {"index": 102, "column": "col_102"}

    column_defs = opts["columnDefs"]
    index_col = column_defs[0]
    assert index_col["field"] == "index"
    assert index_col["headerName"] == "#"
    assert index_col["pinned"] == "left"
    assert index_col["minWidth"] >= 56
    assert column_defs[1]["field"] == "column"
