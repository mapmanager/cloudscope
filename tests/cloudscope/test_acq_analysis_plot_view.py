"""Tests for AcqAnalysisPlotView non-UI behavior."""

from __future__ import annotations

from acqstore.acq_image.analysis.model import AnalysisKey, AnalysisPlotData  # noqa: F401
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import AnalysisCompleted, AnalysisKind
from cloudscope.events.roi import RoiChanged, RoiChangeKind
from cloudscope.state import PrimarySelection
from cloudscope.views.acq_analysis_plot_view import AcqAnalysisPlotView
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId


class FakeAnalysis:
    """Small analysis object exposing plot data."""

    def __init__(self, plot_data: AnalysisPlotData | None) -> None:
        """Create fake analysis.

        Args:
            plot_data: Plot data to return.
        """
        self._plot_data = plot_data

    def get_plot_data(self) -> AnalysisPlotData | None:
        """Return configured plot data.

        Returns:
            Plot data or None.
        """
        return self._plot_data


class FakeAnalysisSet:
    """Small analysis set with primary-kymograph lookup."""

    def __init__(self) -> None:
        """Create empty fake analysis set."""
        self._primary: dict[tuple[int, int], FakeAnalysis] = {}

    def set_primary_kymograph(
        self,
        *,
        channel: int,
        roi_id: int,
        analysis: FakeAnalysis,
    ) -> None:
        """Register the active primary-kymograph analysis.

        Args:
            channel: Channel index.
            roi_id: ROI identifier.
            analysis: Fake analysis instance.

        Returns:
            None.
        """
        self._primary[(channel, roi_id)] = analysis

    def get_primary_kymograph_analysis(
        self,
        *,
        channel: int,
        roi_id: int,
    ) -> FakeAnalysis | None:
        """Return the primary-kymograph analysis for one selection.

        Args:
            channel: Channel index.
            roi_id: ROI identifier.

        Returns:
            Matching analysis or None.
        """
        return self._primary.get((channel, roi_id))

    def get(self, _key):
        """Return None for any analysis key (no event analyses by default)."""
        return None


class FakeAcqImage:
    """Small AcqImage stand-in."""

    def __init__(self) -> None:
        """Create fake AcqImage with analysis set."""
        self.analysis_set = FakeAnalysisSet()


def test_acq_analysis_plot_view_is_base_view() -> None:
    """AcqAnalysisPlotView should be a display-only BaseView."""
    view = AcqAnalysisPlotView(event_bus=EventBus())

    assert isinstance(view, BaseView)
    assert view.view_id is ViewId.ACQ_ANALYSIS_PLOT
    assert view.disable_when_busy is False


def test_acq_analysis_plot_view_gets_primary_kymograph_plot_data() -> None:
    """View should retrieve plot data for active primary-kymograph analysis."""
    view = AcqAnalysisPlotView(event_bus=EventBus())
    acq_image = FakeAcqImage()
    expected = AnalysisPlotData(
        x=(0.0, 1.0),
        y=(2.0, 3.0),
        x_label="Time (s)",
        y_label="Velocity",
        series_name="Radon velocity",
    )
    acq_image.analysis_set.set_primary_kymograph(
        channel=0, roi_id=2, analysis=FakeAnalysis(expected)
    )
    view.current_acq_image = acq_image
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=2)

    assert view._get_selected_plot_data() is expected


def test_acq_analysis_plot_view_returns_none_without_complete_selection() -> None:
    """Missing channel/ROI should yield no plot data."""
    view = AcqAnalysisPlotView(event_bus=EventBus())
    view.current_acq_image = FakeAcqImage()
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=None)

    assert view._get_selected_plot_data() is None


def test_acq_analysis_plot_view_refreshes_on_matching_analysis_completed() -> None:
    """Matching AnalysisCompleted should refresh regardless of analysis kind."""
    view = AcqAnalysisPlotView(event_bus=EventBus())
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=1)
    calls = []
    view._refresh_plot = lambda: calls.append("refresh")  # type: ignore[method-assign]

    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
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
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="other", channel=0, roi_id=1),
            success=True,
        )
    )

    assert calls == ["refresh", "refresh"]


def test_acq_analysis_plot_view_refreshes_on_roi_changed_for_current_file() -> None:
    """RoiChanged for the current file should refresh the plot."""
    view = AcqAnalysisPlotView(event_bus=EventBus())
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=1)
    calls = []
    view._refresh_plot = lambda: calls.append("refresh")  # type: ignore[method-assign]

    view._on_roi_changed(
        RoiChanged(
            operation=RoiChangeKind.DELETE,
            selection=PrimarySelection(file_id="file", channel=0, roi_id=None),
        )
    )
    view._on_roi_changed(
        RoiChanged(
            operation=RoiChangeKind.DELETE,
            selection=PrimarySelection(file_id="other", channel=0, roi_id=None),
        )
    )

    assert calls == ["refresh"]


# ---- additional coverage tests ----


from cloudscope.events.acq_image_events import (
    AcqImageEventSelectionChanged,
    AcqImageEventsChanged,
    AcqImageEventXRangeSelectedIntent,
    EventEditMode,
)
from cloudscope.events.analysis import (
    BeginPlotXRangeSelection,
    CancelPlotXRangeSelection,
)
from cloudscope.views.acq_analysis_plot_view import (
    _OverlayRowObject,
    _overlay_rows_to_objects,
)


class _FakeEvents:
    """Stand-in for EChartWidget.events tracker."""

    def __init__(self) -> None:
        self.set_events_calls: list[list[object]] = []
        self.selections: list[str | None] = []
        self.visibility: list[bool] = []
        self._raise_on_select = False

    def set_events(self, events) -> None:
        self.set_events_calls.append(list(events))

    def select_event(self, event_id):
        if self._raise_on_select:
            raise KeyError("not found")
        self.selections.append(event_id)

    def set_visible(self, visible) -> None:
        self.visibility.append(bool(visible))


class _FakeChart:
    """Minimal stand-in for EChartWidget supporting plot tests."""

    def __init__(self) -> None:
        self.events = _FakeEvents()
        self.cleared = 0
        self.line_calls: list[dict[str, object]] = []
        self.begin_x = 0
        self.cancel_x = 0
        self.x_min: float | None = None
        self.x_max: float | None = None
        self.x_reset = 0

    def clear(self) -> None:
        self.cleared += 1

    def set_line_data(self, **kwargs) -> None:
        self.line_calls.append(dict(kwargs))

    def begin_select_x_range(self) -> None:
        self.begin_x += 1

    def cancel_select_x_range(self) -> None:
        self.cancel_x += 1

    def set_x_axis_limits(self, x_min, x_max) -> None:
        self.x_min = x_min
        self.x_max = x_max

    def reset_x_axis_limits(self) -> None:
        self.x_reset += 1


class _FakeLabel:
    def __init__(self) -> None:
        self.text = ""


def _view_with_fake_chart() -> AcqAnalysisPlotView:
    view = AcqAnalysisPlotView(event_bus=EventBus())
    view._chart = _FakeChart()  # type: ignore[assignment]
    view._status_label = _FakeLabel()  # type: ignore[assignment]
    return view


# ---- _refresh_plot ----


def test_refresh_plot_clears_chart_and_sets_status_when_no_plot_data() -> None:
    """When no plot data is available, the chart should clear and the status update."""
    view = _view_with_fake_chart()
    view.current_acq_image = FakeAcqImage()
    view.current_selection = PrimarySelection(file_id=None, channel=None, roi_id=None)

    view._refresh_plot()

    assert view._chart.cleared == 1
    assert view._status_label.text == "No file selected"


def test_refresh_plot_sets_line_data_for_available_plot() -> None:
    """A valid primary-kymograph analysis should push line data and overlays."""
    view = _view_with_fake_chart()
    view.current_acq_image = FakeAcqImage()
    view.current_selection = PrimarySelection(file_id="file", channel=0, roi_id=2)
    plot = AnalysisPlotData(
        x=(0.0, 1.0, 2.0),
        y=(0.5, 1.0, 1.5),
        x_label="Time (s)",
        y_label="Velocity",
        series_name="Radon velocity",
    )
    view.current_acq_image.analysis_set.set_primary_kymograph(
        channel=0, roi_id=2, analysis=FakeAnalysis(plot)
    )

    view._refresh_plot()

    assert view._chart.cleared == 0
    assert view._chart.line_calls[-1]["x"] == (0.0, 1.0, 2.0)
    assert "3 points" in view._status_label.text


def test_refresh_plot_noop_when_no_chart() -> None:
    """Without chart/status objects the method should be a no-op."""
    view = AcqAnalysisPlotView(event_bus=EventBus())
    view._refresh_plot()


# ---- _empty_message ----


def test_empty_message_paths() -> None:
    """_empty_message should report the missing selection level."""
    view = _view_with_fake_chart()
    view.current_selection = PrimarySelection(file_id=None, channel=None, roi_id=None)
    assert view._empty_message() == "No file selected"
    view.current_selection = PrimarySelection(file_id="f", channel=None, roi_id=None)
    assert view._empty_message() == "No channel selected"
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=None)
    assert view._empty_message() == "No ROI selected"
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    assert "No primary-kymograph analysis" in view._empty_message()


# ---- set/reset x axis limits ----


def test_set_x_axis_limits_forwards_to_chart() -> None:
    """set_x_axis_limits should forward bounds to the chart."""
    view = _view_with_fake_chart()
    view.set_x_axis_limits(1.0, 5.0)

    assert view._chart.x_min == 1.0
    assert view._chart.x_max == 5.0


def test_set_x_axis_limits_noop_when_chart_missing() -> None:
    """Setting x axis limits without a chart should be a silent no-op."""
    view = AcqAnalysisPlotView(event_bus=EventBus())
    view.set_x_axis_limits(0.0, 10.0)


def test_reset_x_axis_limits_forwards_to_chart() -> None:
    """reset_x_axis_limits should call the chart equivalent."""
    view = _view_with_fake_chart()
    view.reset_x_axis_limits()

    assert view._chart.x_reset == 1


def test_reset_x_axis_limits_noop_when_chart_missing() -> None:
    """Reset without a chart should be a no-op."""
    view = AcqAnalysisPlotView(event_bus=EventBus())
    view.reset_x_axis_limits()


# ---- _on_begin_plot_x_range_selection ----


def test_on_begin_plot_x_range_selection_starts_chart_for_matching_selection() -> None:
    """A matching selection should start chart x-range mode."""
    view = _view_with_fake_chart()
    sel = PrimarySelection(file_id="f", channel=0, roi_id=1)
    view.current_selection = sel

    view._on_begin_plot_x_range_selection(BeginPlotXRangeSelection(selection=sel))

    assert view._chart.begin_x == 1


def test_on_begin_plot_x_range_selection_ignored_for_mismatched_selection() -> None:
    """Mismatched selection should not enter x-range mode."""
    view = _view_with_fake_chart()
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)

    view._on_begin_plot_x_range_selection(
        BeginPlotXRangeSelection(selection=PrimarySelection(file_id="g", channel=0, roi_id=1))
    )

    assert view._chart.begin_x == 0


def test_on_begin_plot_x_range_selection_noop_without_chart() -> None:
    """Without a chart, the handler should silently return."""
    view = AcqAnalysisPlotView(event_bus=EventBus())
    view._on_begin_plot_x_range_selection(
        BeginPlotXRangeSelection(selection=PrimarySelection(file_id="f", channel=0, roi_id=1))
    )


# ---- _on_cancel_plot_x_range_selection ----


def test_on_cancel_plot_x_range_selection_calls_chart_cancel() -> None:
    """Cancel should always call chart.cancel_select_x_range."""
    view = _view_with_fake_chart()
    view._on_cancel_plot_x_range_selection(CancelPlotXRangeSelection())

    assert view._chart.cancel_x == 1


def test_on_cancel_plot_x_range_selection_noop_without_chart() -> None:
    """Cancel without a chart should be a no-op."""
    view = AcqAnalysisPlotView(event_bus=EventBus())
    view._on_cancel_plot_x_range_selection(CancelPlotXRangeSelection())


# ---- _on_acq_image_events_changed ----


def test_on_acq_image_events_changed_updates_chart_state_for_matching_selection() -> None:
    """Matching events should push overlays, selection, and visibility into chart.events."""
    view = _view_with_fake_chart()
    sel = PrimarySelection(file_id="f", channel=0, roi_id=1)
    view.current_selection = sel

    view._on_acq_image_events_changed(
        AcqImageEventsChanged(
            selection=sel,
            rows=[{"id": "5", "x0": 1.0, "x1": 2.0, "event_type": "user"}],
            selected_event_id=5,
            visible=False,
            edit_mode=EventEditMode.NONE,
        )
    )

    assert view._chart.events.set_events_calls
    assert view._chart.events.selections == ["5"]
    assert view._chart.events.visibility == [False]


def test_on_acq_image_events_changed_ignored_for_other_selection() -> None:
    """Events for other selections should not touch chart state."""
    view = _view_with_fake_chart()
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)

    view._on_acq_image_events_changed(
        AcqImageEventsChanged(
            selection=PrimarySelection(file_id="other", channel=0, roi_id=1),
            rows=[],
            selected_event_id=None,
            visible=True,
            edit_mode=EventEditMode.NONE,
        )
    )

    assert view._chart.events.set_events_calls == []


def test_on_acq_image_events_changed_noop_without_chart() -> None:
    """No chart should not raise."""
    view = AcqAnalysisPlotView(event_bus=EventBus())
    view._on_acq_image_events_changed(
        AcqImageEventsChanged(
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            rows=[],
            selected_event_id=None,
            visible=True,
            edit_mode=EventEditMode.NONE,
        )
    )


# ---- _on_acq_image_event_selection_changed ----


def test_event_selection_changed_forwards_string_id() -> None:
    """Selection changes should be forwarded as string event ids."""
    view = _view_with_fake_chart()

    view._on_acq_image_event_selection_changed(AcqImageEventSelectionChanged(selected_event_id=12))

    assert view._chart.events.selections == ["12"]


def test_event_selection_changed_clears_selection_on_keyerror() -> None:
    """If the chart raises KeyError, the selection should be cleared."""
    view = _view_with_fake_chart()
    view._chart.events._raise_on_select = True
    view._chart.events.select_event = view._chart.events.select_event  # noqa: B018  silence linter

    class _ErrEvents:
        def __init__(self) -> None:
            self.cleared = False

        def select_event(self, value):
            if value is not None:
                raise KeyError("missing")
            self.cleared = True

    view._chart.events = _ErrEvents()  # type: ignore[assignment]

    view._on_acq_image_event_selection_changed(AcqImageEventSelectionChanged(selected_event_id=99))

    assert view._chart.events.cleared is True  # type: ignore[attr-defined]


def test_event_selection_changed_noop_without_chart() -> None:
    """Should not raise without a chart."""
    view = AcqAnalysisPlotView(event_bus=EventBus())
    view._on_acq_image_event_selection_changed(AcqImageEventSelectionChanged(selected_event_id=None))


# ---- _on_x_range_selected ----


def test_on_x_range_selected_publishes_intent_with_current_selection() -> None:
    """User-selected x range should publish AcqImageEventXRangeSelectedIntent."""
    bus = EventBus()
    intents: list[AcqImageEventXRangeSelectedIntent] = []
    bus.subscribe(AcqImageEventXRangeSelectedIntent, intents.append)
    view = AcqAnalysisPlotView(event_bus=bus)
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)

    view._on_x_range_selected(1.5, 3.5)

    assert len(intents) == 1
    assert intents[0].x0 == 1.5
    assert intents[0].x1 == 3.5
    assert intents[0].selection.file_id == "f"


# ---- _overlay_rows_to_objects ----


def test_overlay_rows_to_objects_translates_row_fields() -> None:
    """_overlay_rows_to_objects should expose id/x0/x1/event_type."""
    row = {"id": 7, "x0": 1.0, "x1": 2.5, "event_type": "auto"}
    objects = _overlay_rows_to_objects([row])

    assert len(objects) == 1
    assert objects[0].id == "7"
    assert objects[0].x0 == 1.0
    assert objects[0].x1 == 2.5
    assert objects[0].event_type == "auto"


def test_overlay_row_object_defaults_event_type_to_user() -> None:
    """A row without event_type should default to 'user'."""
    obj = _OverlayRowObject({"id": "1", "x0": 0.0, "x1": 1.0})
    assert obj.event_type == "user"
