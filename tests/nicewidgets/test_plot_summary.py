"""Tests for NicePool plot summary builders."""

from __future__ import annotations

import pandas as pd

from nicewidgets.nicepool.dataframe_processor import DataFrameProcessor
from nicewidgets.nicepool.figure_generator import FigureGenerator
from nicewidgets.nicepool.plot_state import PlotState, PlotType
from nicewidgets.nicepool.plot_summary import build_scatter_summary, build_swarm_summary
from nicewidgets.nicepool.pre_filter_conventions import PRE_FILTER_NONE


def test_build_scatter_summary_when_xcol_equals_group_col() -> None:
    """Scatter summary must not duplicate the group column when xcol == group_col."""
    state = PlotState(
        pre_filter={"parent": PRE_FILTER_NONE},
        xcol="parent",
        ycol="velocity_velocity_mean",
        plot_type=PlotType.SCATTER,
        group_col="parent",
        color_grouping="roi_id",
    )
    tmp = pd.DataFrame(
        {
            "x": ["folder-a", "folder-a"],
            "y": [1.0, 2.0],
            "row_id": ["r1", "r2"],
            "file_stem": ["a", "a"],
            "color": ["folder-a", "folder-a"],
            "symbol": ["1", "2"],
        }
    )

    summary = build_scatter_summary(
        state,
        tmp,
        state.xcol,
        state.ycol,
        state.group_col,
        state.color_grouping,
    )

    assert "parent" in summary.columnar.columns
    assert "roi_id" in summary.columnar.columns
    assert list(summary.columnar.columns).count("parent") == 1


def test_build_swarm_summary_when_color_grouping_equals_group_col() -> None:
    """Swarm summary must not duplicate columns when color_grouping == group_col."""
    state = PlotState(
        pre_filter={"parent": PRE_FILTER_NONE},
        xcol="parent",
        ycol="velocity_velocity_mean",
        plot_type=PlotType.SWARM,
        group_col="parent",
        color_grouping="parent",
    )
    tmp = pd.DataFrame(
        {
            "x": ["folder-a", "folder-b"],
            "y": [1.0, 2.0],
            "row_id": ["r1", "r2"],
            "file_stem": ["a", "b"],
            "color": ["folder-a", "folder-b"],
        }
    )

    summary = build_swarm_summary(state, tmp, state.group_col, state.color_grouping)

    assert "parent" in summary.columnar.columns
    assert list(summary.columnar.columns).count("parent") == 1


def test_figure_generator_split_scatter_when_xcol_equals_group_col() -> None:
    """Split scatter replot must succeed when xcol and group_col share a name."""
    df = pd.DataFrame(
        [
            {
                "pool_row_id": "a",
                "parent": "folder-a",
                "roi_id": 1,
                "velocity_velocity_mean": 1.5,
            },
            {
                "pool_row_id": "b",
                "parent": "folder-a",
                "roi_id": 2,
                "velocity_velocity_mean": 2.5,
            },
        ]
    )
    state = PlotState(
        pre_filter={},
        xcol="parent",
        ycol="velocity_velocity_mean",
        plot_type=PlotType.SCATTER,
        group_col="parent",
        color_grouping="roi_id",
    )
    processor = DataFrameProcessor(df, pre_filter_columns=(), unique_row_id_col="pool_row_id")
    generator = FigureGenerator(processor, unique_row_id_col="pool_row_id")

    fig_dict, summary = generator.make_figure(df, state)

    assert fig_dict
    assert summary.columnar is not None
    assert "parent" in summary.columnar.columns
