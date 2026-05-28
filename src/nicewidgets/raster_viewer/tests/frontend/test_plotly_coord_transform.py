"""Tests for Plotly row/col coordinate transform."""

from __future__ import annotations

from nicewidgets.raster_viewer.backend.image_model import RasterGridSpec, RowColBounds
from nicewidgets.raster_viewer.frontend.plotly_coord_transform import PlotlyCoordTransform, merge_partial_relayout


def test_plot_xy_round_trip() -> None:
    """Plot extents should round-trip to row/col and back consistently."""
    grid = RasterGridSpec(dx=0.1, dy=0.5, x_unit='s', y_unit='m')
    t = PlotlyCoordTransform(nrows=100, ncols=200, grid=grid)
    b0 = RowColBounds(row_min=10.0, row_max=40.0, col_min=5.0, col_max=25.0)
    x_lo, x_hi = t.row_col_to_plot_x_range(b0)
    y_lo, y_hi = t.row_col_to_plot_y_range(b0)
    b1 = t.plot_xy_ranges_to_row_col(x_lo, x_hi, y_lo, y_hi)
    assert abs(b1.row_min - b0.row_min) < 1e-6
    assert abs(b1.row_max - b0.row_max) < 1e-6
    assert abs(b1.col_min - b0.col_min) < 1e-6
    assert abs(b1.col_max - b0.col_max) < 1e-6


def test_row_col_to_plot_y_range_is_bottom_up() -> None:
    """Y range should be low-to-high for Plotly's bottom-left display origin."""
    grid = RasterGridSpec(dx=0.1, dy=0.5, x_unit='s', y_unit='m')
    t = PlotlyCoordTransform(nrows=100, ncols=200, grid=grid)
    bounds = RowColBounds(row_min=0.0, row_max=100.0, col_min=5.0, col_max=25.0)

    assert t.row_col_to_plot_y_range(bounds) == (2.5, 12.5)


def test_merge_partial_relayout_fills_missing_axis() -> None:
    """Merge should add x or y keys when only one axis appears in relayout."""
    grid = RasterGridSpec(dx=1.0, dy=1.0, x_unit='', y_unit='')
    t = PlotlyCoordTransform(nrows=8, ncols=16, grid=grid)
    fb = RowColBounds(row_min=0.0, row_max=8.0, col_min=0.0, col_max=16.0)
    merged = merge_partial_relayout({'xaxis.range[0]': 2.0, 'xaxis.range[1]': 5.0}, t, fb)
    assert 'yaxis.range' in merged
    assert 'xaxis.range[0]' in merged
