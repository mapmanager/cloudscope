"""Tests for PrimaryImageView handler logic using a fake viewer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from acqstore.acq_image.analysis.model import AnalysisOverlayTraceData
from acqstore.acq_image.roi import (
    ImageBounds,
    RectRoiBounds,
    RectROI,
    RoiSet,
)
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import AnalysisCompleted, AnalysisKind
from cloudscope.events.roi import RoiChanged, RoiChangeKind
from cloudscope.state import PrimarySelection
from cloudscope.views.primary_image_view import (
    PrimaryImageView,
    roi_local_traces_to_plotly_overlays,
)
from nicewidgets.raster_viewer.backend.image_model import RasterGridSpec


@dataclass
class FakeViewer:
    """Stand-in for PlotlyRasterViewer used to assert handler calls."""

    rois_calls: list[list[object]] = field(default_factory=list)
    selected_roi: list[int | None] = field(default_factory=list)
    clear_trace_calls: int = 0
    set_trace_calls: list[list[object]] = field(default_factory=list)

    def set_rois(self, overlays):
        self.rois_calls.append(list(overlays))

    def select_roi(self, roi_id):
        self.selected_roi.append(roi_id)

    def clear_trace_overlays(self):
        self.clear_trace_calls += 1

    def set_trace_overlays(self, overlays):
        self.set_trace_calls.append(list(overlays))


def _view_with_fake_viewer() -> PrimaryImageView:
    view = PrimaryImageView(EventBus())
    view._viewer = FakeViewer()  # type: ignore[assignment]
    return view


# ---- _refresh_roi_overlays ----


def test_refresh_roi_overlays_clears_when_no_acq_image_or_grid() -> None:
    """Missing acq image or grid should reset the viewer ROI list to []."""
    view = _view_with_fake_viewer()

    view._refresh_roi_overlays(acq_image=None, grid=None)

    assert view._viewer.rois_calls[-1] == []
    assert view._viewer.selected_roi == []


def test_refresh_roi_overlays_pushes_rect_rois_and_selection() -> None:
    """A grid + acq image with one rect ROI should push the overlay and selection."""
    view = _view_with_fake_viewer()

    class _Img:
        def __init__(self) -> None:
            self.rois = RoiSet(ImageBounds(width=20, height=10))
            self.rois.create_rect_roi(
                RectRoiBounds(dim0_start=1, dim0_stop=4, dim1_start=2, dim1_stop=6)
            )

    img = _Img()
    grid = RasterGridSpec(dx=1.0, dy=1.0, x_unit="row", y_unit="col")
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)

    view._refresh_roi_overlays(acq_image=img, grid=grid)

    assert view._viewer.rois_calls
    assert view._viewer.selected_roi[-1] == 1


# ---- _refresh_diameter_trace_overlays ----


def test_refresh_diameter_trace_overlays_clears_without_acq_image() -> None:
    """Without an acq image or grid, the viewer trace overlays should be cleared."""
    view = _view_with_fake_viewer()
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)

    view._refresh_diameter_trace_overlays(acq_image=None, grid=None)

    assert view._viewer.clear_trace_calls == 1


def test_refresh_diameter_trace_overlays_clears_without_channel_or_roi() -> None:
    """Missing channel/ROI should clear overlays."""
    view = _view_with_fake_viewer()
    view.current_selection = PrimarySelection(file_id="f", channel=None, roi_id=None)
    grid = RasterGridSpec(dx=1.0, dy=1.0, x_unit="r", y_unit="c")

    view._refresh_diameter_trace_overlays(acq_image=object(), grid=grid)

    assert view._viewer.clear_trace_calls == 1


def test_refresh_diameter_trace_overlays_clears_when_no_analysis() -> None:
    """A complete selection but no diameter analysis should clear overlays."""

    class _Set:
        def get(self, _key):
            return None

    class _Img:
        analysis_set = _Set()

    view = _view_with_fake_viewer()
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    grid = RasterGridSpec(dx=1.0, dy=1.0, x_unit="r", y_unit="c")

    view._refresh_diameter_trace_overlays(acq_image=_Img(), grid=grid)

    assert view._viewer.clear_trace_calls == 1


def test_refresh_diameter_trace_overlays_clears_when_roi_not_rect() -> None:
    """If the selected ROI is not rectangular, overlays should be cleared."""

    class _Analysis:
        def get_overlay_traces(self):
            return ()

    class _Rois:
        def get(self, _id):
            return object()

    class _Set:
        def get(self, _key):
            return _Analysis()

    class _Img:
        analysis_set = _Set()
        rois = _Rois()

    view = _view_with_fake_viewer()
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    grid = RasterGridSpec(dx=1.0, dy=1.0, x_unit="r", y_unit="c")

    view._refresh_diameter_trace_overlays(acq_image=_Img(), grid=grid)

    assert view._viewer.clear_trace_calls == 1


def test_refresh_diameter_trace_overlays_pushes_overlays_when_analysis_present() -> None:
    """A diameter analysis with an overlay trace + rect ROI should push overlays."""

    class _Analysis:
        def get_overlay_traces(self):
            return (
                AnalysisOverlayTraceData(
                    trace_id="t1",
                    x=(0.0, 1.0, 2.0),
                    y=(0.0, 1.0, 0.0),
                    color="red",
                    name="edge",
                    visible=True,
                ),
            )

    class _Set:
        def get(self, _key):
            return _Analysis()

    rect = RectROI(
        roi_id=1,
        bounds=RectRoiBounds(dim0_start=0, dim0_stop=4, dim1_start=0, dim1_stop=4),
    )

    class _Rois:
        def get(self, _id):
            return rect

    class _Img:
        analysis_set = _Set()
        rois = _Rois()

    view = _view_with_fake_viewer()
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    grid = RasterGridSpec(dx=1.0, dy=1.0, x_unit="r", y_unit="c")

    view._refresh_diameter_trace_overlays(acq_image=_Img(), grid=grid)

    assert view._viewer.clear_trace_calls == 0
    assert view._viewer.set_trace_calls
    assert view._viewer.set_trace_calls[-1][0].trace_id == "t1"


# ---- _on_analysis_completed selectivity ----


def test_on_analysis_completed_only_acts_for_diameter_matching_selection() -> None:
    """Should ignore non-DIAMETER kinds and mismatched selections."""
    view = _view_with_fake_viewer()
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    calls: list[str] = []
    view._refresh_diameter_trace_overlays_from_current_selection = lambda: calls.append("r")  # type: ignore[method-assign]

    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.RADON_VELOCITY,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            success=True,
        )
    )
    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.DIAMETER,
            selection=PrimarySelection(file_id="other", channel=0, roi_id=1),
            success=True,
        )
    )
    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.DIAMETER,
            selection=PrimarySelection(file_id="f", channel=1, roi_id=1),
            success=True,
        )
    )
    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.DIAMETER,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=2),
            success=True,
        )
    )

    assert calls == []

    view._on_analysis_completed(
        AnalysisCompleted(
            analysis_kind=AnalysisKind.DIAMETER,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
            success=True,
        )
    )

    assert calls == ["r"]


# ---- _on_roi_changed ----


def test_on_roi_changed_refreshes_only_for_current_file() -> None:
    """ROI mutations for other files should not trigger overlay refresh."""
    view = _view_with_fake_viewer()
    view.current_selection = PrimarySelection(file_id="f", channel=0, roi_id=1)
    calls: list[str] = []
    view._refresh_roi_overlays_from_current_selection = lambda: calls.append("roi")  # type: ignore[method-assign]
    view._refresh_diameter_trace_overlays_from_current_selection = lambda: calls.append("trace")  # type: ignore[method-assign]

    view._on_roi_changed(
        RoiChanged(
            operation=RoiChangeKind.EDIT,
            selection=PrimarySelection(file_id="other", channel=0, roi_id=1),
        )
    )
    view._on_roi_changed(
        RoiChanged(
            operation=RoiChangeKind.EDIT,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
        )
    )

    assert calls == ["roi", "trace"]


def test_on_roi_changed_noop_when_no_current_file() -> None:
    """No current file id should skip the refresh."""
    view = _view_with_fake_viewer()
    view.current_selection = PrimarySelection()
    calls: list[str] = []
    view._refresh_roi_overlays_from_current_selection = lambda: calls.append("roi")  # type: ignore[method-assign]

    view._on_roi_changed(
        RoiChanged(
            operation=RoiChangeKind.ADD,
            selection=PrimarySelection(file_id="f", channel=0, roi_id=1),
        )
    )

    assert calls == []


# ---- roi_local_traces_to_plotly_overlays ----


def test_roi_local_traces_to_plotly_overlays_offsets_by_roi_bounds() -> None:
    """ROI-local coords should be shifted by the ROI top-left and scaled by grid."""
    roi = RectROI(
        roi_id=1,
        bounds=RectRoiBounds(dim0_start=2, dim0_stop=5, dim1_start=4, dim1_stop=9),
    )
    grid = RasterGridSpec(dx=0.5, dy=0.25, x_unit="s", y_unit="um")
    trace = AnalysisOverlayTraceData(
        trace_id="t",
        x=(0.0, 1.0),
        y=(0.0, 2.0),
        color="blue",
        name="left",
        visible=True,
    )

    overlays = roi_local_traces_to_plotly_overlays((trace,), roi=roi, grid=grid)

    assert len(overlays) == 1
    assert overlays[0].x == (1.0, 2.0)
    assert overlays[0].y == (1.0, 3.0)
    assert overlays[0].color == "blue"


def test_roi_local_traces_to_plotly_overlays_skips_invisible_or_empty() -> None:
    """Invisible traces or empty x should be filtered out."""
    roi = RectROI(
        roi_id=1,
        bounds=RectRoiBounds(dim0_start=0, dim0_stop=2, dim1_start=0, dim1_stop=2),
    )
    grid = RasterGridSpec(dx=1.0, dy=1.0, x_unit="r", y_unit="c")
    traces = (
        AnalysisOverlayTraceData(trace_id="invisible", x=(0.0,), y=(0.0,), visible=False),
        AnalysisOverlayTraceData(trace_id="empty", x=(), y=(), visible=True),
        AnalysisOverlayTraceData(trace_id="keep", x=(0.0,), y=(0.0,), visible=True),
    )

    overlays = roi_local_traces_to_plotly_overlays(traces, roi=roi, grid=grid)

    assert [o.trace_id for o in overlays] == ["keep"]


# ---- on_primary_selection_changed and refresh_from_state ----


def test_on_primary_selection_changed_delegates_to_refresh() -> None:
    """on_primary_selection_changed should delegate to _refresh_raster_from_current_selection."""
    view = _view_with_fake_viewer()
    calls: list[str] = []
    view._refresh_raster_from_current_selection = lambda: calls.append("r")  # type: ignore[method-assign]

    view.on_primary_selection_changed()

    assert calls == ["r"]


def test_refresh_from_state_delegates_to_refresh() -> None:
    """refresh_from_state should delegate to _refresh_raster_from_current_selection."""
    view = _view_with_fake_viewer()
    calls: list[str] = []
    view._refresh_raster_from_current_selection = lambda: calls.append("r")  # type: ignore[method-assign]

    view.refresh_from_state()

    assert calls == ["r"]
