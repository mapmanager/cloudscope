"""Tests for CloudScope primary-image ROI overlay conversion."""

from __future__ import annotations

from acqstore.acq_image.roi import ImageBounds, RectRoiBounds, RectROI, RoiSet, LineEndpoints
from cloudscope.views.primary_image_view import (
    _rect_roi_overlay_from_rect_roi,
    _rect_roi_overlays_from_acq_image,
)
from nicewidgets.raster_viewer.backend.image_model import RasterGridSpec


class FakeAcqImage:
    """Minimal acquisition image with a ROI set for overlay tests."""

    def __init__(self) -> None:
        self.rois = RoiSet(ImageBounds(width=20, height=10))


def test_rect_roi_overlay_uses_physical_plot_coordinates() -> None:
    """RectROI dim0/dim1 bounds should map to Plotly x/y physical coordinates."""
    roi = RectROI(
        roi_id=5,
        bounds=RectRoiBounds(dim0_start=2, dim0_stop=6, dim1_start=3, dim1_stop=9),
    )
    grid = RasterGridSpec(dx=0.5, dy=0.25, x_unit='s', y_unit='um')

    overlay = _rect_roi_overlay_from_rect_roi(roi, grid=grid)

    assert overlay.roi_id == 5
    assert overlay.x0 == 1.0
    assert overlay.x1 == 3.0
    assert overlay.y0 == 0.75
    assert overlay.y1 == 2.25


def test_rect_roi_overlays_ignore_line_rois() -> None:
    """Only rectangular ROIs should be displayed in ROI-3A."""
    acq_image = FakeAcqImage()
    rect = acq_image.rois.create_rect_roi(
        RectRoiBounds(dim0_start=1, dim0_stop=2, dim1_start=3, dim1_stop=4)
    )
    acq_image.rois.create_line_roi(LineEndpoints(row0=0, col0=0, row1=1, col1=1))
    grid = RasterGridSpec(dx=2.0, dy=3.0, x_unit='row', y_unit='col')

    overlays = _rect_roi_overlays_from_acq_image(acq_image, grid=grid)

    assert [overlay.roi_id for overlay in overlays] == [rect.roi_id]
