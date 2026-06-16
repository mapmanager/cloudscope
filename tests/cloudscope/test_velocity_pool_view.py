"""Headless tests for VelocityPoolView callbacks."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from acqstore.analysis_pool.velocity_analysis_pool import VelocityAnalysisPool
from cloudscope.event_bus import EventBus
from cloudscope.events.selection import SelectFileIntent
from cloudscope.views import velocity_pool_view as velocity_pool_view_module
from cloudscope.views.velocity_pool_view import VelocityPoolView
from nicewidgets.nicepool.config import NicePoolConfig
from nicewidgets.nicepool.plot_state import PlotType
from nicewidgets.nicepool.pre_filter_conventions import PRE_FILTER_NONE


class FakeRoot:
    """Minimal root element used by BaseView.after_build in headless tests."""

    visible = True

    def update(self) -> None:
        """Mimic a NiceGUI element update call."""


class FakeNicePool:
    """Capture NicePool construction arguments without building NiceGUI."""

    instances: list["FakeNicePool"] = []

    def __init__(
        self,
        df: pd.DataFrame,
        *,
        config: NicePoolConfig,
        on_row_selected: Any,
    ) -> None:
        self.df = df
        self.config = config
        self.on_row_selected = on_row_selected
        FakeNicePool.instances.append(self)

    def build(self, parent: Any | None = None) -> FakeRoot:
        """Return a fake root for the CloudScope view."""
        _ = parent
        return FakeRoot()

    def set_dataframe(self, df: pd.DataFrame) -> None:
        """Record refresh data."""
        self.df = df


def test_velocity_pool_view_row_selection_publishes_select_file_intent() -> None:
    """Selecting a pool row should request the matching file/channel/ROI."""
    bus = EventBus()
    intents: list[SelectFileIntent] = []
    bus.subscribe(SelectFileIntent, intents.append)
    view = VelocityPoolView(event_bus=bus, app_state=None)

    view._on_row_selected(
        "row-a",
        {"path": "file-a", "channel": 2, "roi_id": 5},
    )

    assert intents == [SelectFileIntent(file_id="file-a", channel=2, roi_id=5)]


def test_empty_velocity_pool_dataframe_uses_full_backend_schema() -> None:
    """Fallback DataFrame should expose all pool columns for nicepool auto-detection."""
    view = VelocityPoolView(event_bus=EventBus(), app_state=None)

    df = view._pool_dataframe_from_state()

    expected_columns = list(VelocityAnalysisPool.base_columns)
    for prefix, analysis_cls in VelocityAnalysisPool.analysis_specs:
        expected_columns.extend(f"{prefix}_{column}" for column in analysis_cls.get_summary_columns())
    assert list(df.columns) == expected_columns
    assert {"accept", "channel", "roi_id", "parent", "velocity_velocity_mean"}.issubset(df.columns)


def test_velocity_pool_view_configures_default_plot_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Velocity pool should pass CloudScope-specific plot defaults to NicePool."""
    FakeNicePool.instances.clear()
    monkeypatch.setattr(velocity_pool_view_module, "NicePool", FakeNicePool)
    view = VelocityPoolView(event_bus=EventBus(), app_state=None, initially_visible=False)

    view.build()

    assert len(FakeNicePool.instances) == 1
    config = FakeNicePool.instances[0].config
    state = config.plot_state
    assert state is not None
    assert state.pre_filter == {
        "accept": PRE_FILTER_NONE,
        "channel": PRE_FILTER_NONE,
        "roi_id": PRE_FILTER_NONE,
    }
    assert state.xcol == "parent"
    assert state.ycol == "velocity_velocity_mean"
    assert state.plot_type is PlotType.SWARM
    assert state.group_col == "parent"
    assert state.color_grouping == "parent"
    assert config.show_table_widget is False
    assert config.enable_config_persistence is False
