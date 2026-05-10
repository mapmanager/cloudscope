"""Tests for Plotly rectangular ROI overlay helpers."""

from __future__ import annotations


from nicewidgets.raster_viewer.frontend.roi_overlay import (
    PlotlyRoiOverlayLayer,
    RectRoiOverlay,
    RectRoiStyleConfig,
)
from nicewidgets.raster_viewer.frontend.plotly_viewer import PlotlyRasterViewer


def test_roi_shape_name_is_stable() -> None:
    """ROI shape names should encode stable integer ROI ids."""
    assert PlotlyRoiOverlayLayer.shape_name(7) == 'roi:7'


def test_set_rois_replaces_roi_shapes_but_preserves_non_roi_shapes() -> None:
    """ROI replacement should keep unrelated Plotly shapes."""
    layer = PlotlyRoiOverlayLayer()
    layer.set_rois([RectRoiOverlay(roi_id=1, x0=0, x1=2, y0=1, y1=3)])

    merged = layer.merge_shapes([
        {'type': 'line', 'name': 'crosshair'},
        {'type': 'rect', 'name': 'roi:99'},
    ])

    assert [shape['name'] for shape in merged] == ['crosshair', 'roi:1']


def test_select_roi_updates_selected_style() -> None:
    """Selected ROI should use selected style values."""
    style = RectRoiStyleConfig(
        line_width=1,
        line_color='normal-line',
        fill_color='normal-fill',
        selected_line_width=5,
        selected_line_color='selected-line',
        selected_fill_color='selected-fill',
    )
    layer = PlotlyRoiOverlayLayer(style=style)
    layer.set_rois([
        RectRoiOverlay(roi_id=1, x0=0, x1=2, y0=1, y1=3),
        RectRoiOverlay(roi_id=2, x0=4, x1=5, y0=6, y1=7),
    ])
    layer.select_roi(2)

    shapes = {shape['name']: shape for shape in layer.to_shapes()}
    assert shapes['roi:1']['line']['color'] == 'normal-line'
    assert shapes['roi:2']['line']['color'] == 'selected-line'
    assert shapes['roi:2']['line']['width'] == 5
    assert shapes['roi:2']['fillcolor'] == 'selected-fill'


def test_add_roi_replaces_duplicate_and_delete_removes() -> None:
    """Adding duplicate ROI ids should replace and delete should remove."""
    layer = PlotlyRoiOverlayLayer()
    layer.add_roi(RectRoiOverlay(roi_id=3, x0=0, x1=1, y0=0, y1=1))
    layer.add_roi(RectRoiOverlay(roi_id=3, x0=10, x1=11, y0=12, y1=13))
    assert len(layer.to_shapes()) == 1
    assert layer.to_shapes()[0]['x0'] == 10.0

    layer.select_roi(3)
    layer.delete_roi(3)
    assert layer.to_shapes() == []
    assert layer.selected_roi_id is None


def test_plotly_raster_viewer_roi_api_mutates_layout_shapes_without_plot_update() -> None:
    """Viewer ROI APIs should mutate layout.shapes without requiring a Plotly element."""
    viewer = PlotlyRasterViewer()
    viewer.figure.setdefault('layout', {})['shapes'] = [{'type': 'line', 'name': 'line:1'}]

    viewer.set_rois([RectRoiOverlay(roi_id=1, x0=0, x1=1, y0=2, y1=3)])
    assert [shape['name'] for shape in viewer.figure['layout']['shapes']] == ['line:1', 'roi:1']

    viewer.select_roi(1)
    roi_shape = viewer.figure['layout']['shapes'][1]
    assert roi_shape['line']['width'] == 3

    viewer.delete_roi(1)
    assert [shape['name'] for shape in viewer.figure['layout']['shapes']] == ['line:1']
