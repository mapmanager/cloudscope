"""Tests for diameter trace overlay coordinate translation."""

from __future__ import annotations

from acqstore.acq_image.analysis.model import AnalysisOverlayTraceData
from acqstore.acq_image.roi import RectROI, RectRoiBounds
from cloudscope.views.primary_image_view import roi_local_traces_to_plotly_overlays
from nicewidgets.raster_viewer.backend.image_model import RasterGridSpec


def test_roi_local_traces_translate_to_full_image_plot_coords() -> None:
    """ROI-local traces should shift by ROI origin times grid spacing."""
    roi = RectROI(
        roi_id=1,
        bounds=RectRoiBounds(dim0_start=10, dim0_stop=20, dim1_start=5, dim1_stop=15),
    )
    grid = RasterGridSpec(dx=0.001, dy=0.2, x_unit="s", y_unit="um")
    traces = (
        AnalysisOverlayTraceData(
            trace_id="diameter_left_edge",
            x=(0.0, 0.001),
            y=(1.0, 2.0),
            color="cyan",
            name="Left edge",
        ),
    )
    overlays = roi_local_traces_to_plotly_overlays(traces, roi=roi, grid=grid)
    assert len(overlays) == 1
    assert overlays[0].x == (0.01, 0.011)
    assert overlays[0].y == (2.0, 3.0)
