"""Headless tests for PlotPoolController orchestration APIs."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from nicewidgets.nicepool.plot_pool_controller import PlotPoolConfig, PlotPoolController
from nicewidgets.nicepool.plot_state import PlotState, PlotType
from nicewidgets.nicepool.pre_filter_conventions import PRE_FILTER_NONE


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "pool_row_id": ["a", "b", "c"],
            "parent": ["g1", "g1", "g2"],
            "roi_id": [1, 2, 1],
            "velocity_mean": [1.0, 2.0, 3.0],
            "diameter": [10.0, 11.0, 12.0],
        }
    )


def _controller(tmp_path: Path, **config_overrides: object) -> PlotPoolController:
    config = PlotPoolConfig(
        unique_row_id_col="pool_row_id",
        pre_filter_columns=["roi_id"],
        enable_config_persistence=False,
        plot_preset_path=tmp_path / "nicepoolplots.json",
        plot_state=PlotState(
            pre_filter={"roi_id": PRE_FILTER_NONE},
            xcol="diameter",
            ycol="velocity_mean",
            plot_type=PlotType.SWARM,
            group_col="parent",
            color_grouping="roi_id",
        ),
        **config_overrides,
    )
    return PlotPoolController(_df(), config=config)


def test_save_load_delete_plot_preset_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Preset APIs should persist and restore layout plus plot states."""
    monkeypatch.setattr("nicewidgets.nicepool.plot_pool_controller.ui.notify", MagicMock())
    controller = _controller(tmp_path)
    controller.layout = "1x2"

    assert controller.save_current_plot_preset(" Velocity Plot ") is True
    assert controller.get_plot_preset_names() == ["Velocity Plot"]

    controller.layout = "1x1"
    controller.plot_states[0] = PlotState(
        pre_filter={"roi_id": PRE_FILTER_NONE},
        xcol="parent",
        ycol="velocity_mean",
        plot_type=PlotType.SCATTER,
        group_col="parent",
    )

    assert controller.load_plot_preset("Velocity Plot") is True
    assert controller.layout == "1x2"
    assert controller.plot_states[0].plot_type == PlotType.SWARM
    assert controller.plot_states[0].group_col == "parent"

    assert controller.delete_plot_preset("Velocity Plot") is True
    assert controller.get_plot_preset_names() == []


def test_save_current_plot_preset_rejects_empty_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty preset names should fail fast before touching disk."""
    notifications: list[str] = []
    monkeypatch.setattr(
        "nicewidgets.nicepool.plot_pool_controller.ui.notify",
        lambda message, *, type="info": notifications.append(message),
    )
    controller = _controller(tmp_path)

    assert controller.save_current_plot_preset("   ") is False
    assert controller.get_plot_preset_names() == []
    assert notifications


def test_update_df_is_noop_before_build(tmp_path: Path) -> None:
    """update_df should not raise when the controller UI has not been built yet."""
    controller = _controller(tmp_path)
    refreshed = _df().assign(velocity_mean=[4.0, 5.0, 6.0])

    controller.update_df(refreshed)

    assert controller.df["velocity_mean"].tolist() == [1.0, 2.0, 3.0]


def test_update_df_requires_unique_row_id_column(tmp_path: Path) -> None:
    """update_df must validate the unique row-id contract."""
    controller = _controller(tmp_path)
    controller._control_panel_container = MagicMock()

    with pytest.raises(ValueError, match="pool_row_id"):
        controller.update_df(pd.DataFrame({"parent": ["g1"]}))


def test_select_points_by_row_id_delegates_to_selection_handler(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Public API should select by stringified row id through the handler."""
    controller = _controller(tmp_path)
    calls: list[str] = []
    monkeypatch.setattr(
        controller._selection_handler,
        "select_by_row_id",
        lambda row_id, plot_states: calls.append(row_id),
    )

    controller.select_points_by_row_id("b")

    assert calls == ["b"]


def test_validate_plot_state_columns_repairs_stale_x_and_y_columns(tmp_path: Path) -> None:
    """Loaded states with missing columns should be repaired against the current df."""
    controller = _controller(tmp_path)
    stale = PlotState(
        pre_filter={"roi_id": PRE_FILTER_NONE},
        xcol="missing_x",
        ycol="missing_y",
        plot_type=PlotType.SCATTER,
        group_col="missing_group",
        color_grouping="missing_color",
    )

    repaired = controller._validate_plot_state_columns(stale)

    assert repaired.xcol == "diameter"
    assert repaired.ycol == "velocity_mean"
    assert repaired.group_col is None
    assert repaired.color_grouping is None
