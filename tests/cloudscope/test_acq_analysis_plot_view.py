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
