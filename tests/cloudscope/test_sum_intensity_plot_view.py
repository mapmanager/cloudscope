"""Tests for SumIntensityPlotView non-UI behavior."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

import numpy as np
import pytest

from acqstore.acq_image.analysis.diameter_analysis.diameter_analysis import DiameterAnalysis
from acqstore.acq_image.analysis.model import AnalysisKey, AnalysisPlotData
from acqstore.acq_image.analysis.sum_intensity_analysis.sum_intensity_analysis import (
    SumIntensityAnalysis,
)
from acqstore.acq_image.analysis.sum_intensity_analysis.sum_intensity_core import (
    ResultPoints,
    ResultTrace,
    SumIntensityEventPointKey,
    SumIntensityTraceKey,
)
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import AnalysisCompleted, AnalysisKind
from cloudscope.events.roi import RoiChangeKind, RoiChanged
from cloudscope.events.selection import FileSelectionChanged
from cloudscope.events.theme import ThemeChanged
from cloudscope.events.x_range import PrimaryXRangeChanged, SetPrimaryXRangeIntent
from cloudscope.state import PrimarySelection
import cloudscope.views.sum_intensity_plot_view as sum_intensity_plot_view_module
from cloudscope.views.base_view import BaseView
from cloudscope.views.sum_intensity_plot_view import SumIntensityPlotView
from cloudscope.views.view_ids import ViewId
from nicewidgets.plotly_plot.models import MeasurementChangeEvent, PlotlyScatterData, PlotlySeriesMenuItem, PlotlyTraceData


class _FakePlot:
    """Small stand-in for PlotlyPlotWidget used by view unit tests."""

    def __init__(self) -> None:
        """Create an empty fake plot."""
        self.traces: list[PlotlyTraceData] = []
        self.scatters: list[PlotlyScatterData] = []
        self.set_series_calls = 0
        self.x_limits: tuple[float | None, float | None] | None = None
        self.x_reset_calls = 0
        self.dark_mode: bool | None = None
        self._series_visibility: dict[str, bool] = {}
        self.placeholder_text: str | None = None
        self.y2_label: str | None = None
        self.x_label: str | None = None
        self.y_label: str | None = None

    def register_series_menu_items(self, items: list[PlotlySeriesMenuItem]) -> None:
        """Record menu defaults while preserving existing visibility choices."""
        for item in items:
            if item.series_name not in self._series_visibility:
                self._series_visibility[item.series_name] = bool(item.default_visible)

    def is_series_visible(self, series_name: str) -> bool:
        """Return stored visibility for one series."""
        if series_name in self._series_visibility:
            return self._series_visibility[series_name]
        return True

    def set_series(
        self,
        *,
        traces: list[PlotlyTraceData] | tuple[PlotlyTraceData, ...] = (),
        scatters: list[PlotlyScatterData] | tuple[PlotlyScatterData, ...] = (),
    ) -> None:
        """Record one batched series replacement."""
        self.set_series_calls += 1
        self.traces = list(traces)
        self.scatters = list(scatters)

    def set_x_axis_limits(self, x_min: float | None, x_max: float | None) -> None:
        """Record finite axis limits."""
        self.x_limits = (x_min, x_max)

    def reset_x_axis_limits(self) -> None:
        """Record an axis reset."""
        self.x_reset_calls += 1
        self.x_limits = (None, None)

    def set_dark_mode(self, enabled: bool) -> None:
        """Record dark-mode theme updates."""
        self.dark_mode = bool(enabled)

    def set_placeholder_text(self, message: str | None) -> None:
        """Record centered placeholder text."""
        self.placeholder_text = message.strip() if message else None

    def set_y2_label(self, label: str) -> None:
        """Record right y-axis label updates."""
        self.y2_label = str(label)

    def set_x_label(self, label: str) -> None:
        """Record x-axis label updates."""
        self.x_label = str(label)

    def set_y_label(self, label: str) -> None:
        """Record y-axis label updates."""
        self.y_label = str(label)


def _view_with_fake_plot() -> SumIntensityPlotView:
    """Create a view with fake child plot."""
    view = SumIntensityPlotView(event_bus=EventBus())
    view._plot = _FakePlot()  # type: ignore[assignment]
    view._plot.register_series_menu_items(SumIntensityPlotView._sum_intensity_series_menu_items())  # type: ignore[attr-defined]
    return view


class _FakeAnalysisSet:
    """Fake analysis set with key-based lookup."""

    def __init__(self) -> None:
        """Create an empty analysis set."""
        self._items: dict[AnalysisKey, object] = {}

    def set(self, key: AnalysisKey, analysis: object) -> None:
        """Register an analysis by key."""
        self._items[key] = analysis

    def get(self, key: AnalysisKey) -> object | None:
        """Return an analysis by key."""
        return self._items.get(key)


class _FakeAcqImage:
    """Fake AcqImage with an analysis set."""

    def __init__(self) -> None:
        """Create fake acquisition image."""
        self.analysis_set = _FakeAnalysisSet()


class _FakeDiameterAnalysis(DiameterAnalysis):
    """Fake diameter analysis with deterministic plot data."""

    def __init__(self) -> None:
        """Create fake analysis without running backend computation."""
        super().__init__(channel=0, roi_id=1)

    def get_plot_data(self) -> AnalysisPlotData:
        """Return diameter-versus-time plot data."""
        return AnalysisPlotData(
            x=(0.0, 1.0, 2.0),
            y=(10.0, 12.0, 11.0),
            x_label="Time (s)",
            y_label="Diameter (um)",
            series_name="Diameter",
        )


class _FakeSumIntensityAnalysis(SumIntensityAnalysis):
    """Concrete SumIntensityAnalysis with deterministic public API values."""

    def __init__(self) -> None:
        """Create fake analysis without running backend computation."""
        super().__init__(channel=0, roi_id=1)

    def get_trace(self, key: SumIntensityTraceKey) -> ResultTrace:
        """Return deterministic continuous traces."""
        names = {
            SumIntensityTraceKey.DF_F_SIGNAL: "df/f0 signal",
            SumIntensityTraceKey.D_DF_F_SIGNAL: "Derivative of df/f0",
        }
        if key not in names:
            raise KeyError(key)
        return ResultTrace(
            key=key,
            name=names[key],
            x=np.asarray([0.0, 1.0, 2.0], dtype=float),
            y=np.asarray([0.0, 0.5, 0.25], dtype=float),
            x_label="Time (s)",
            y_label="df/f0",
            metadata={},
        )

    def get_event_points(self, key: SumIntensityEventPointKey) -> ResultPoints:
        """Return deterministic event points."""
        if key is SumIntensityEventPointKey.ONSETS:
            return ResultPoints(
                key=key,
                name="Onsets",
                x=np.asarray([0.5], dtype=float),
                y=np.asarray([0.2], dtype=float),
                x_label="Time (s)",
                y_label="df/f0",
                metadata={},
            )
        if key is SumIntensityEventPointKey.PEAKS:
            return ResultPoints(
                key=key,
                name="Peaks",
                x=np.asarray([1.0], dtype=float),
                y=np.asarray([0.5], dtype=float),
                x_label="Time (s)",
                y_label="df/f0",
                metadata={},
            )
        raise KeyError(key)

    def get_plot_data(self) -> AnalysisPlotData:
        """Return canonical df/f0 plot data for axis-label tests."""
        trace = self.get_trace(SumIntensityTraceKey.DF_F_SIGNAL)
        return AnalysisPlotData(
            x=tuple(float(value) for value in trace.x.tolist()),
            y=tuple(float(value) for value in trace.y.tolist()),
            x_label=trace.x_label,
            y_label=trace.y_label,
            series_name=trace.name,
        )

    def get_width_trace(self, peak_width_level=None):
        """Return one width trace in a tuple."""
        _ = peak_width_level
        return (
            ResultTrace(
                key="p50",
                name="Peak width 50",
                x=np.asarray([0.75, 1.25, np.nan], dtype=float),
                y=np.asarray([0.3, 0.3, np.nan], dtype=float),
                x_label="Time (s)",
                y_label="Signal",
                metadata={},
            ),
        )

    def get_summary_values(self) -> dict[str, object]:
        """Return deterministic summary values."""
        return {"num_peaks": 1, "f0_baseline": 1.2345}


class _BadSumIntensityAnalysis(_FakeSumIntensityAnalysis):
    """Fake analysis that raises while building traces."""

    def get_trace(self, key: SumIntensityTraceKey) -> ResultTrace:
        """Raise a missing-column error."""
        _ = key
        raise KeyError("missing trace")


def test_sum_intensity_series_menu_items_place_diameter_last_with_separator() -> None:
    """Diameter toggle should be last among series items with a separator before it."""
    items = SumIntensityPlotView._sum_intensity_series_menu_items()

    assert items[-1].series_name == "Diameter"
    assert items[-1].separator_before is True
    assert all(not item.separator_before for item in items[:-1])


def test_sum_intensity_plot_view_identity() -> None:
    """SumIntensityPlotView should expose its stable view id."""
    view = SumIntensityPlotView(event_bus=EventBus())

    assert isinstance(view, BaseView)
    assert view.view_id is ViewId.SUM_INTENSITY_PLOT
    assert view.disable_when_busy is False


def test_get_selected_sum_intensity_analysis_returns_matching_analysis() -> None:
    """The view should look up sum-intensity analysis by selected channel/ROI."""
    view = SumIntensityPlotView(event_bus=EventBus())
    acq_image = _FakeAcqImage()
    analysis = _FakeSumIntensityAnalysis()
    acq_image.analysis_set.set(AnalysisKey("sum_intensity", 0, 1), analysis)
    view.current_acq_image = acq_image
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=1)

    assert view._get_selected_sum_intensity_analysis() is analysis


def test_get_selected_sum_intensity_analysis_returns_none_for_incomplete_selection() -> None:
    """Missing channel/ROI should yield no analysis."""
    view = SumIntensityPlotView(event_bus=EventBus())
    view.current_acq_image = _FakeAcqImage()
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=None)

    assert view._get_selected_sum_intensity_analysis() is None


def test_get_selected_diameter_analysis_returns_matching_analysis() -> None:
    """The view should look up diameter analysis by selected channel/ROI."""
    view = SumIntensityPlotView(event_bus=EventBus())
    acq_image = _FakeAcqImage()
    analysis = _FakeDiameterAnalysis()
    acq_image.analysis_set.set(AnalysisKey("diameter", 0, 1), analysis)
    view.current_acq_image = acq_image
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=1)

    assert view._get_selected_diameter_analysis() is analysis


def test_refresh_plot_clears_when_no_analysis() -> None:
    """No selected analysis should clear traces and show an empty state."""
    view = _view_with_fake_plot()
    view.current_acq_image = _FakeAcqImage()
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=1)

    view._refresh_plot()

    assert view._plot.set_series_calls == 1
    assert view._plot.traces == []
    assert view._plot.scatters == []
    assert "No sum-intensity analysis" in (view._plot.placeholder_text or "")


def test_refresh_plot_pushes_traces_scatters_and_widths() -> None:
    """A valid analysis should update continuous traces and sparse overlays."""
    view = _view_with_fake_plot()
    acq_image = _FakeAcqImage()
    acq_image.analysis_set.set(AnalysisKey("sum_intensity", 0, 1), _FakeSumIntensityAnalysis())
    view.current_acq_image = acq_image
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=1)

    view._refresh_plot()

    trace_names = [trace.name for trace in view._plot.traces]
    scatter_names = [scatter.name for scatter in view._plot.scatters]
    assert view._plot.set_series_calls == 1
    assert trace_names == ["df/f0 signal", "Derivative of df/f0", "Peak width 50"]
    assert scatter_names == ["Onsets", "Peaks"]
    assert view._plot.traces[0].y_axis == "left"
    assert view._plot.traces[1].y_axis == "right"
    assert view._plot.traces[1].visible is False
    assert view._plot.traces[2].visible is True
    assert all(scatter.visible for scatter in view._plot.scatters)
    assert view._plot.placeholder_text is None


def test_refresh_plot_includes_diameter_trace_when_analysis_present() -> None:
    """Diameter overlay should append on y2 when diameter analysis exists."""
    view = _view_with_fake_plot()
    acq_image = _FakeAcqImage()
    acq_image.analysis_set.set(AnalysisKey("sum_intensity", 0, 1), _FakeSumIntensityAnalysis())
    acq_image.analysis_set.set(AnalysisKey("diameter", 0, 1), _FakeDiameterAnalysis())
    view.current_acq_image = acq_image
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=1)

    view._refresh_plot()

    diameter = next((trace for trace in view._plot.traces if trace.name == "Diameter"), None)
    assert diameter is not None
    assert diameter.y_axis == "right"
    assert diameter.visible is False


def test_refresh_plot_omits_diameter_trace_when_toggle_on_but_no_analysis() -> None:
    """Diameter toggle may persist without data until a diameter result exists."""
    view = _view_with_fake_plot()
    acq_image = _FakeAcqImage()
    acq_image.analysis_set.set(AnalysisKey("sum_intensity", 0, 1), _FakeSumIntensityAnalysis())
    view.current_acq_image = acq_image
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=1)
    view._plot._series_visibility["Diameter"] = True  # type: ignore[attr-defined]

    view._refresh_plot()

    assert "Diameter" not in [trace.name for trace in view._plot.traces]


def test_refresh_plot_shows_diameter_when_toggle_on() -> None:
    """Diameter trace should honor context-menu visibility when data exists."""
    view = _view_with_fake_plot()
    acq_image = _FakeAcqImage()
    acq_image.analysis_set.set(AnalysisKey("sum_intensity", 0, 1), _FakeSumIntensityAnalysis())
    acq_image.analysis_set.set(AnalysisKey("diameter", 0, 1), _FakeDiameterAnalysis())
    view.current_acq_image = acq_image
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=1)
    view._plot._series_visibility["Diameter"] = True  # type: ignore[attr-defined]

    view._refresh_plot()

    diameter = next(trace for trace in view._plot.traces if trace.name == "Diameter")
    assert diameter.visible is True


def test_apply_y2_label_clears_when_derivative_and_diameter_hidden() -> None:
    """Right y-axis title should be empty when no right-axis overlays are visible."""
    view = _view_with_fake_plot()
    acq_image = _FakeAcqImage()
    acq_image.analysis_set.set(AnalysisKey("sum_intensity", 0, 1), _FakeSumIntensityAnalysis())
    acq_image.analysis_set.set(AnalysisKey("diameter", 0, 1), _FakeDiameterAnalysis())
    view.current_acq_image = acq_image
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=1)

    view._refresh_plot()

    assert view._plot.y2_label == ""


def test_refresh_plot_applies_df_f0_axis_labels_from_plot_data() -> None:
    """Y-axis title should come from canonical df/f0 plot data, not a hardcoded label."""
    view = _view_with_fake_plot()
    acq_image = _FakeAcqImage()
    acq_image.analysis_set.set(AnalysisKey("sum_intensity", 0, 1), _FakeSumIntensityAnalysis())
    view.current_acq_image = acq_image
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=1)

    view._refresh_plot()

    assert view._plot.x_label == "Time (s)"
    assert view._plot.y_label == "df/f0"


def test_apply_y2_label_uses_derivative_label_when_derivative_visible() -> None:
    """Derivative overlay should set the derivative right y-axis title."""
    view = _view_with_fake_plot()
    acq_image = _FakeAcqImage()
    acq_image.analysis_set.set(AnalysisKey("sum_intensity", 0, 1), _FakeSumIntensityAnalysis())
    view.current_acq_image = acq_image
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=1)
    view._plot._series_visibility["Derivative of df/f0"] = True  # type: ignore[attr-defined]

    view._refresh_plot()

    assert view._plot.y2_label == "d(df/f0)/dt (1/s)"


def test_apply_y2_label_uses_diameter_label_when_diameter_only_visible() -> None:
    """Diameter-only overlay should set the diameter right y-axis title."""
    view = _view_with_fake_plot()
    acq_image = _FakeAcqImage()
    acq_image.analysis_set.set(AnalysisKey("sum_intensity", 0, 1), _FakeSumIntensityAnalysis())
    acq_image.analysis_set.set(AnalysisKey("diameter", 0, 1), _FakeDiameterAnalysis())
    view.current_acq_image = acq_image
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=1)
    view._plot._series_visibility["Diameter"] = True  # type: ignore[attr-defined]

    view._refresh_plot()

    assert view._plot.y2_label == "Diameter (um)"


def test_refresh_plot_preserves_series_visibility_across_selection() -> None:
    """Trace toggle choices should survive file/channel/ROI refresh until reload."""
    view = _view_with_fake_plot()
    acq_image = _FakeAcqImage()
    acq_image.analysis_set.set(AnalysisKey("sum_intensity", 0, 1), _FakeSumIntensityAnalysis())
    view.current_acq_image = acq_image
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=1)

    view._refresh_plot()
    view._plot._series_visibility["Onsets"] = False  # type: ignore[attr-defined]

    view.current_selection = PrimarySelection(file_id="other", channel=0, roi_id=1)
    view._refresh_plot()

    onsets = next(scatter for scatter in view._plot.scatters if scatter.name == "Onsets")
    assert onsets.visible is False
    assert view._plot.is_series_visible("Derivative of df/f0") is False


def test_refresh_plot_reports_backend_plot_error() -> None:
    """Backend trace errors should clear plot and surface a status message."""
    view = _view_with_fake_plot()
    acq_image = _FakeAcqImage()
    acq_image.analysis_set.set(AnalysisKey("sum_intensity", 0, 1), _BadSumIntensityAnalysis())
    view.current_acq_image = acq_image
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=1)

    view._refresh_plot()

    assert view._plot.traces == []
    assert "Sum-intensity plot unavailable" in (view._plot.placeholder_text or "")


def test_matching_analysis_completion_refreshes_plot() -> None:
    """Matching SUM_INTENSITY and DIAMETER completions should refresh the plot."""
    view = SumIntensityPlotView(event_bus=EventBus())
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=1)
    calls: list[str] = []
    view._refresh_plot_from_current_selection = lambda: calls.append("refresh")  # type: ignore[method-assign]

    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.SUM_INTENSITY,
            selection=PrimarySelection(file_id="file", channel=0, roi_id=1),
            success=True,
        )
    )
    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.DIAMETER,
            selection=PrimarySelection(file_id="file", channel=0, roi_id=1),
            success=True,
        )
    )
    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.SUM_INTENSITY,
            selection=PrimarySelection(file_id="other", channel=0, roi_id=1),
            success=True,
        )
    )

    assert calls == ["refresh", "refresh"]


def test_roi_changed_refreshes_for_current_file_only() -> None:
    """ROI changes for the selected file should refresh the plot."""
    view = SumIntensityPlotView(event_bus=EventBus())
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=1)
    calls: list[str] = []
    view._refresh_plot_from_current_selection = lambda: calls.append("refresh")  # type: ignore[method-assign]

    view._on_roi_changed(
        RoiChanged(
            operation=RoiChangeKind.DELETE,
            selection=PrimarySelection(file_id="file", channel=0, roi_id=1),
        )
    )
    view._on_roi_changed(
        RoiChanged(
            operation=RoiChangeKind.DELETE,
            selection=PrimarySelection(file_id="other", channel=0, roi_id=1),
        )
    )

    assert calls == ["refresh"]


def test_plot_x_range_callback_publishes_set_primary_x_range_intent() -> None:
    """User Plotly x-range changes should become app-level x-range intents."""
    bus = EventBus()
    intents: list[SetPrimaryXRangeIntent] = []
    bus.subscribe(SetPrimaryXRangeIntent, intents.append)
    view = SumIntensityPlotView(event_bus=bus)

    view._on_plot_x_range_changed(2.0, 4.0)

    assert intents == [SetPrimaryXRangeIntent(x_min=2.0, x_max=4.0)]


def test_sum_intensity_plot_view_skips_self_echo_after_plot_originated_range() -> None:
    """Plot-originated x-range should not round-trip ``set_x_axis_limits``."""
    view = _view_with_fake_plot()

    view._on_plot_x_range_changed(2.0, 8.0)
    view._on_primary_x_range_changed(PrimaryXRangeChanged(x_min=2.0, x_max=8.0))

    assert view._plot.x_limits is None
    assert view._primary_x_range == (2.0, 8.0)


def test_primary_x_range_changed_applies_to_plot() -> None:
    """PrimaryXRangeChanged should push finite limits to the child plot."""
    view = _view_with_fake_plot()

    view._on_primary_x_range_changed(PrimaryXRangeChanged(x_min=1.0, x_max=5.0))

    assert view._plot.x_limits == (1.0, 5.0)


def test_primary_x_range_changed_resets_plot_for_auto_range() -> None:
    """Auto range state should reset the child plot."""
    view = _view_with_fake_plot()

    view._on_primary_x_range_changed(PrimaryXRangeChanged(x_min=None, x_max=None))

    assert view._plot.x_reset_calls == 1


def test_measurement_callback_stores_event_for_future_intent_wiring() -> None:
    """Measurement callbacks should be captured without mutating app state yet."""
    view = SumIntensityPlotView(event_bus=EventBus())
    event = MeasurementChangeEvent(
        name="threshold",
        kind="line",
        orientation="horizontal",
        position=1.5,
    )

    view._on_measurement_changed(event)

    assert view.last_measurement_event is event


def test_theme_changed_applies_dark_mode_to_plot() -> None:
    """ThemeChanged should push dark-mode state to the child plot."""
    view = _view_with_fake_plot()

    view._on_theme_changed(ThemeChanged(dark_mode=True))

    assert view._plot.dark_mode is True


def test_sync_theme_from_provider_uses_current_app_theme() -> None:
    """refresh_from_state should resync theme when a provider is available."""
    view = SumIntensityPlotView(
        event_bus=EventBus(),
        dark_mode=False,
        dark_mode_provider=lambda: True,
    )
    view._plot = _FakePlot()  # type: ignore[assignment]

    view._sync_theme_from_provider()

    assert view._plot.dark_mode is True


class _FakePlotContainer:
    """Minimal NiceGUI container stand-in for build tests."""

    def classes(self, *_args: object, **_kwargs: object) -> _FakePlotContainer:
        return self


class _BuildFakePlotlyWidget(_FakePlot):
    """PlotlyPlotWidget stand-in used by build() tests."""

    def __init__(self, **_kwargs: object) -> None:
        super().__init__()
        self.container = _FakePlotContainer()


def test_stale_plot_refresh_generation_is_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Build-time empty refreshes must not clear a later selection refresh."""
    scheduled: list[Coroutine[Any, Any, None]] = []

    def _capture_schedule(coro: Coroutine[Any, Any, None]) -> None:
        scheduled.append(coro)

    monkeypatch.setattr(sum_intensity_plot_view_module, '_schedule_coro', _capture_schedule)

    view = _view_with_fake_plot()
    refresh_calls: list[str] = []
    view._refresh_plot = lambda: refresh_calls.append('refresh')  # type: ignore[method-assign]

    view._refresh_plot_from_current_selection()
    view._refresh_plot_from_current_selection()

    assert len(scheduled) == 2
    assert refresh_calls == []

    asyncio.run(scheduled[0])

    assert refresh_calls == []


def test_build_schedules_refresh_plot_from_current_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """build() should schedule plot refresh via _refresh_plot_from_current_selection."""
    scheduled: list[Coroutine[Any, Any, None]] = []

    def _capture_schedule(coro: Coroutine[Any, Any, None]) -> None:
        scheduled.append(coro)

    monkeypatch.setattr(
        sum_intensity_plot_view_module,
        'PlotlyPlotWidget',
        _BuildFakePlotlyWidget,
    )
    monkeypatch.setattr(sum_intensity_plot_view_module, '_schedule_coro', _capture_schedule)

    view = SumIntensityPlotView(event_bus=EventBus(), initially_visible=False)
    refresh_calls: list[str] = []
    view._refresh_plot = lambda: refresh_calls.append('refresh')  # type: ignore[method-assign]

    view.build()

    assert view.is_built
    assert len(scheduled) == 1
    assert refresh_calls == []

    asyncio.run(scheduled[0])

    assert refresh_calls == ['refresh']


def test_on_primary_selection_changed_schedules_refresh_plot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Selection changes should schedule async plot refresh, not push synchronously."""
    scheduled: list[Coroutine[Any, Any, None]] = []

    def _capture_schedule(coro: Coroutine[Any, Any, None]) -> None:
        scheduled.append(coro)

    monkeypatch.setattr(sum_intensity_plot_view_module, '_schedule_coro', _capture_schedule)

    view = SumIntensityPlotView(event_bus=EventBus())
    refresh_calls: list[str] = []
    view._refresh_plot = lambda: refresh_calls.append('refresh')  # type: ignore[method-assign]

    view.on_primary_selection_changed()

    assert len(scheduled) == 1
    assert refresh_calls == []
    asyncio.run(scheduled[0])
    assert refresh_calls == ['refresh']


def test_refresh_from_state_schedules_refresh_plot(monkeypatch: pytest.MonkeyPatch) -> None:
    """refresh_from_state should schedule async plot refresh after theme sync."""
    scheduled: list[Coroutine[Any, Any, None]] = []

    def _capture_schedule(coro: Coroutine[Any, Any, None]) -> None:
        scheduled.append(coro)

    monkeypatch.setattr(sum_intensity_plot_view_module, '_schedule_coro', _capture_schedule)

    view = _view_with_fake_plot()
    refresh_calls: list[str] = []
    view._refresh_plot = lambda: refresh_calls.append('refresh')  # type: ignore[method-assign]

    view.refresh_from_state()

    assert len(scheduled) == 1
    assert refresh_calls == []
    asyncio.run(scheduled[0])
    assert refresh_calls == ['refresh']


def test_file_selection_changed_schedules_plot_data_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bootstrap-style FileSelectionChanged should schedule a deferred plot push."""
    scheduled: list[Coroutine[Any, Any, None]] = []

    def _capture_schedule(coro: Coroutine[Any, Any, None]) -> None:
        scheduled.append(coro)

    monkeypatch.setattr(sum_intensity_plot_view_module, '_schedule_coro', _capture_schedule)

    bus = EventBus()
    view = SumIntensityPlotView(event_bus=bus)
    view._plot = _FakePlot()  # type: ignore[assignment]
    view._plot.register_series_menu_items(SumIntensityPlotView._sum_intensity_series_menu_items())  # type: ignore[attr-defined]
    view._disposed = False
    view.add_subscription(bus.subscribe(FileSelectionChanged, view._on_file_selection_changed))

    acq = _FakeAcqImage()
    analysis = _FakeSumIntensityAnalysis()
    acq.analysis_set.set(AnalysisKey('sum_intensity', 0, 1), analysis)

    bus.publish(
        FileSelectionChanged(
            file_id='file',
            acq_image=acq,
            channel=0,
            roi_id=1,
        )
    )

    assert len(scheduled) == 1
    asyncio.run(scheduled[0])

    assert view._plot.set_series_calls >= 1
    assert view._plot.traces
    assert view._plot.traces[0].name == 'df/f0 signal'
