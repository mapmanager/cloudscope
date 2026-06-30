"""Headless tests for VelocityPoolView callbacks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from acqstore.analysis_pool.sum_intensity_analysis_pool import SumIntensityAnalysisPool
from acqstore.analysis_pool.velocity_analysis_pool import VelocityAnalysisPool
from cloudscope.event_bus import EventBus
from cloudscope.events.selection import SelectFileIntent
from cloudscope.events.sum_intensity_pool import (
    SumIntensityPoolChanged,
    SumIntensityPoolChangeKind,
)
from cloudscope.events.theme import ThemeChanged
from cloudscope.events.velocity_pool import VelocityPoolChanged, VelocityPoolChangeKind
from cloudscope.views import velocity_pool_view as velocity_pool_view_module
from cloudscope.views.sum_intensity_pool_plot_config import SUM_INTENSITY_POOL_INITIAL_PLOT_CONFIG
from cloudscope.views.velocity_pool_plot_config import VELOCITY_POOL_INITIAL_PLOT_CONFIG
from cloudscope.views.velocity_pool_view import VelocityPoolView
from nicewidgets.nicepool.config import NicePoolConfig


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
        self.set_dataframe_calls: list[pd.DataFrame] = []
        self.dark_mode_values: list[bool] = []
        FakeNicePool.instances.append(self)

    def build(self, parent: Any | None = None) -> FakeRoot:
        """Return a fake root for the CloudScope view."""
        _ = parent
        return FakeRoot()

    def set_dataframe(self, df: pd.DataFrame) -> None:
        """Record refresh data."""
        self.df = df
        self.set_dataframe_calls.append(df)

    def set_dark_mode(self, enabled: bool) -> None:
        """Record dark-mode updates."""
        self.dark_mode_values.append(enabled)

    def relayout_plots(self) -> None:
        """Record relayout requests."""
        self.relayout_calls = getattr(self, "relayout_calls", 0) + 1

    def select_points_by_row_id(self, row_id: str) -> None:
        """Record single-row programmatic selection."""
        self.selected_row_ids = [row_id]

    def select_points_by_row_ids(
        self,
        row_ids: set[str] | list[str] | tuple[str, ...],
    ) -> None:
        """Record multi-row programmatic selection."""
        self.selected_row_ids = list(row_ids)


@dataclass
class _FakeSumIntensityPool:
    """Minimal stand-in for sum-intensity pool row-id lookup."""

    row_ids: tuple[str, ...] = ()

    def row_ids_for_selection(
        self,
        file_id: str,
        *,
        channel: int,
        roi_id: int,
        peak_row_types: tuple[str, ...] = ("peak",),
    ) -> tuple[str, ...]:
        _ = (file_id, channel, roi_id, peak_row_types)
        return self.row_ids


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

    df = view._velocity_dataframe_from_state()

    assert list(df.columns) == list(VelocityAnalysisPool.pool_column_names())
    assert {"accept", "channel", "roi_id", "parent", "velocity_mean"}.issubset(df.columns)


def test_empty_peaks_pool_dataframe_uses_full_backend_schema() -> None:
    """Peaks tab fallback DataFrame should expose the sum-intensity pool schema."""
    view = VelocityPoolView(event_bus=EventBus(), app_state=None)

    df = view._peaks_dataframe_from_state()

    assert list(df.columns) == list(SumIntensityAnalysisPool.pool_column_names())
    assert {"peak_row_type", "peak_amplitude", "peak_id"}.issubset(df.columns)


def test_on_hide_sets_disposed_and_unsubscribes() -> None:
    bus = EventBus()
    view = VelocityPoolView(event_bus=bus, app_state=None, initially_visible=True)
    view._built = True
    view.root = FakeRoot()
    view.on_show()
    assert view._subscriptions

    view.on_hide()

    assert view._disposed is True
    assert not view._subscriptions


def test_on_show_clears_disposed() -> None:
    bus = EventBus()
    view = VelocityPoolView(event_bus=bus, app_state=None, initially_visible=False)
    view._built = True
    view.root = FakeRoot()
    view.on_hide()
    assert view._disposed is True

    view.on_show()

    assert view._disposed is False


def test_pool_changed_ignored_after_on_hide() -> None:
    bus = EventBus()
    view = VelocityPoolView(event_bus=bus, app_state=None, initially_visible=False)
    view._disposed = True

    class RecordingPool:
        def __init__(self) -> None:
            self.calls = 0

        def set_dataframe(self, df: pd.DataFrame) -> None:
            self.calls += 1

    velocity_recording = RecordingPool()
    peaks_recording = RecordingPool()
    view._velocity_pool = velocity_recording  # type: ignore[assignment]
    view._peaks_pool = peaks_recording  # type: ignore[assignment]
    view._on_pool_changed(VelocityPoolChanged(change_kind=VelocityPoolChangeKind.REBUILD))

    assert velocity_recording.calls == 0
    assert peaks_recording.calls == 0


def test_refresh_from_state_skipped_once_after_build(monkeypatch: pytest.MonkeyPatch) -> None:
    """Initial build should not immediately rebuild NicePool via on_show refresh."""
    FakeNicePool.instances.clear()
    monkeypatch.setattr(velocity_pool_view_module, "NicePool", FakeNicePool)
    view = VelocityPoolView(event_bus=EventBus(), app_state=None, initially_visible=True)

    view.build()

    assert len(FakeNicePool.instances) == 2
    assert FakeNicePool.instances[0].set_dataframe_calls == []
    assert FakeNicePool.instances[1].set_dataframe_calls == []
    view.refresh_from_state()
    assert len(FakeNicePool.instances[0].set_dataframe_calls) == 1
    assert len(FakeNicePool.instances[1].set_dataframe_calls) == 1


def test_velocity_pool_view_builds_compact_tabs_with_icons(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pool tabs should use compact Quasar props, zero panel padding, and analysis icons."""
    FakeNicePool.instances.clear()
    monkeypatch.setattr(velocity_pool_view_module, "NicePool", FakeNicePool)
    view = VelocityPoolView(event_bus=EventBus(), app_state=None, initially_visible=False)

    view.build()

    assert view._velocity_tab is not None
    assert view._peaks_tab is not None
    assert view._tabs is not None
    assert view._velocity_tab._props["icon"] == "speed"  # noqa: SLF001
    assert view._velocity_tab._props["label"] == "Velocity"  # noqa: SLF001
    assert view._peaks_tab._props["icon"] == "functions"  # noqa: SLF001
    assert view._peaks_tab._props["label"] == "Peaks"  # noqa: SLF001
    tabs_props = str(view._tabs._props)  # noqa: SLF001
    assert "dense" in tabs_props
    assert "inline-label" in tabs_props
    assert velocity_pool_view_module._VELOCITY_POOL_TABS_CLASS in str(view._tabs._classes)  # noqa: SLF001


def test_velocity_pool_view_configures_initial_plot_configs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both tabs should pass CloudScope-owned inline plot configs to NicePool."""
    FakeNicePool.instances.clear()
    monkeypatch.setattr(velocity_pool_view_module, "NicePool", FakeNicePool)
    view = VelocityPoolView(event_bus=EventBus(), app_state=None, initially_visible=False)

    view.build()

    assert len(FakeNicePool.instances) == 2
    velocity_config = FakeNicePool.instances[0].config
    peaks_config = FakeNicePool.instances[1].config
    assert velocity_config.initial_plot_config is VELOCITY_POOL_INITIAL_PLOT_CONFIG
    assert peaks_config.initial_plot_config is SUM_INTENSITY_POOL_INITIAL_PLOT_CONFIG
    velocity_state = velocity_config.initial_plot_config["plot_states"][0]
    expected_velocity = VELOCITY_POOL_INITIAL_PLOT_CONFIG["plot_states"][0]
    assert velocity_state["pre_filter"] == expected_velocity["pre_filter"]
    assert velocity_state["xcol"] == expected_velocity["xcol"]
    assert velocity_state["ycol"] == expected_velocity["ycol"]
    peaks_state = peaks_config.initial_plot_config["plot_states"][0]
    expected_peaks = SUM_INTENSITY_POOL_INITIAL_PLOT_CONFIG["plot_states"][0]
    assert peaks_state["pre_filter"]["peak_row_type"] == expected_peaks["pre_filter"]["peak_row_type"]
    assert peaks_state["ycol"] == expected_peaks["ycol"]
    assert velocity_config.show_table_widget is False
    assert peaks_config.enable_config_persistence is False


def test_primary_selection_syncs_velocity_plot_highlight(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shared primary selection should highlight the matching velocity pool row."""
    FakeNicePool.instances.clear()
    monkeypatch.setattr(velocity_pool_view_module, "NicePool", FakeNicePool)
    view = VelocityPoolView(event_bus=EventBus(), app_state=None, initially_visible=True)
    view.build()
    view._disposed = False
    velocity_pool = FakeNicePool.instances[0]
    peaks_pool = FakeNicePool.instances[1]
    velocity_pool.select_points_by_row_id = MagicMock()  # type: ignore[method-assign]
    peaks_pool.select_points_by_row_ids = MagicMock()  # type: ignore[method-assign]

    view.current_selection.file_id = "/data/sample.oir"
    view.current_selection.channel = 1
    view.current_selection.roi_id = 3

    view.on_primary_selection_changed()

    velocity_pool.select_points_by_row_id.assert_called_once_with(
        "/data/sample.oir|channel=1|roi_id=3"
    )
    peaks_pool.select_points_by_row_ids.assert_not_called()


def test_primary_selection_syncs_all_peaks_plot_highlight(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shared primary selection should highlight all peak rows for the selection."""
    FakeNicePool.instances.clear()
    monkeypatch.setattr(velocity_pool_view_module, "NicePool", FakeNicePool)
    view = VelocityPoolView(event_bus=EventBus(), app_state=None, initially_visible=True)
    view.build()
    view._disposed = False
    peaks_pool = FakeNicePool.instances[1]
    peaks_pool.select_points_by_row_ids = MagicMock()  # type: ignore[method-assign]
    fake_pool = _FakeSumIntensityPool(row_ids=("peak-a", "peak-b"))
    monkeypatch.setattr(view, "_sum_intensity_pool_from_state", lambda: fake_pool)

    view.current_selection.file_id = "/data/sample.oir"
    view.current_selection.channel = 1
    view.current_selection.roi_id = 3

    view.on_primary_selection_changed()

    peaks_pool.select_points_by_row_ids.assert_called_once_with(("peak-a", "peak-b"))


def test_sum_intensity_pool_changed_refreshes_both_tabs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sum-intensity pool events should refresh both embedded NicePool widgets."""
    FakeNicePool.instances.clear()
    monkeypatch.setattr(velocity_pool_view_module, "NicePool", FakeNicePool)
    bus = EventBus()
    view = VelocityPoolView(event_bus=bus, app_state=None, initially_visible=False)
    view.build()
    view._disposed = False
    view._skip_refresh_from_state_once = False
    view.subscribe_events()

    bus.publish(SumIntensityPoolChanged(change_kind=SumIntensityPoolChangeKind.REBUILD))

    assert len(FakeNicePool.instances[0].set_dataframe_calls) == 1
    assert len(FakeNicePool.instances[1].set_dataframe_calls) == 1


def test_velocity_pool_view_initializes_dark_mode_from_constructor(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both tabs should pass initial dark mode into NicePool config."""
    FakeNicePool.instances.clear()
    monkeypatch.setattr(velocity_pool_view_module, "NicePool", FakeNicePool)
    view = VelocityPoolView(event_bus=EventBus(), app_state=None, dark_mode=True, initially_visible=False)

    view.build()

    assert FakeNicePool.instances[0].config.dark_mode is True
    assert FakeNicePool.instances[1].config.dark_mode is True


def test_velocity_pool_view_consumes_theme_changed_event(monkeypatch: pytest.MonkeyPatch) -> None:
    """ThemeChanged should route to both NicePool widgets."""
    FakeNicePool.instances.clear()
    monkeypatch.setattr(velocity_pool_view_module, "NicePool", FakeNicePool)
    bus = EventBus()
    view = VelocityPoolView(event_bus=bus, app_state=None, initially_visible=False)
    view.build()
    view._disposed = False

    view.subscribe_events()
    bus.publish(ThemeChanged(dark_mode=True))

    assert FakeNicePool.instances[0].dark_mode_values == [True]
    assert FakeNicePool.instances[1].dark_mode_values == [True]


def test_velocity_pool_view_refresh_syncs_theme_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hidden views should resync theme from provider on refresh."""
    FakeNicePool.instances.clear()
    monkeypatch.setattr(velocity_pool_view_module, "NicePool", FakeNicePool)
    view = VelocityPoolView(
        event_bus=EventBus(),
        app_state=None,
        dark_mode=False,
        dark_mode_provider=lambda: True,
        initially_visible=True,
    )
    view.build()
    view._disposed = False
    view._skip_refresh_from_state_once = False

    view.refresh_from_state()

    assert FakeNicePool.instances[0].dark_mode_values == [True]
    assert FakeNicePool.instances[1].dark_mode_values == [True]


def test_velocity_pool_view_relayout_plots_delegates_to_active_nicepool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Relayout should forward to the active-tab NicePool widget."""
    FakeNicePool.instances.clear()
    monkeypatch.setattr(velocity_pool_view_module, "NicePool", FakeNicePool)
    view = VelocityPoolView(event_bus=EventBus(), app_state=None, initially_visible=False)
    view.build()
    view._disposed = False

    view.relayout_plots()

    assert FakeNicePool.instances[0].relayout_calls == 1
    assert getattr(FakeNicePool.instances[1], "relayout_calls", 0) == 0
