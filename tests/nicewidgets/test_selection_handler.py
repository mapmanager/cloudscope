"""Tests for PlotSelectionHandler programmatic selection."""

from __future__ import annotations

import pandas as pd

from nicewidgets.nicepool.dataframe_processor import DataFrameProcessor
from nicewidgets.nicepool.figure_generator import FigureGenerator
from nicewidgets.nicepool.plot_state import PlotState, PlotType
from nicewidgets.nicepool.pre_filter_conventions import PRE_FILTER_NONE
from nicewidgets.nicepool.selection_handler import PlotSelectionHandler


def test_select_by_row_id_works_for_swarm_plot() -> None:
    """Programmatic selection should target swarm plots, not only scatter."""
    df = pd.DataFrame(
        [
            {"pool_row_id": "a", "parent": "g1", "roi_id": 1, "velocity_mean": 1.0},
            {"pool_row_id": "b", "parent": "g1", "roi_id": 2, "velocity_mean": 2.0},
        ]
    )
    state = PlotState(
        pre_filter={"parent": PRE_FILTER_NONE},
        xcol="parent",
        ycol="velocity_mean",
        plot_type=PlotType.SWARM,
        group_col="parent",
        color_grouping="roi_id",
    )
    processor = DataFrameProcessor(df, pre_filter_columns=("parent",), unique_row_id_col="pool_row_id")
    generator = FigureGenerator(processor, unique_row_id_col="pool_row_id")
    applied: list[set[str]] = []

    handler = PlotSelectionHandler(
        data_processor=processor,
        figure_generator=generator,
        unique_row_id_col="pool_row_id",
        get_filtered_df=lambda _plot_state: df,
        on_apply_selection=lambda: applied.append(handler.get_selected_row_ids()),
        on_update_label=lambda _count: None,
    )

    handler.select_by_row_id("b", [state])

    assert handler.get_selected_row_ids() == {"b"}
    assert applied == [{"b"}]
