"""Tests for frontend Plotly protocol helpers."""

from __future__ import annotations

import numpy as np

from raster_viewer.backend.image_model import RasterGridSpec, RenderResponse, RowColBounds
from raster_viewer.frontend.plotly_coord_transform import PlotlyCoordTransform
from raster_viewer.frontend.plotly_protocol import (
    DEFAULT_HEATMAP_COLORSCALE,
    PlotlyViewportPayload,
    build_plotly_figure,
    parse_relayout_payload,
)

_GRID = RasterGridSpec(dx=1.0, dy=1.0, x_unit='', y_unit='')


def _png_response() -> RenderResponse:
    return RenderResponse(
        mode='image_png',
        level=1,
        bounds=RowColBounds(row_min=0.0, row_max=10.0, col_min=0.0, col_max=5.0),
        shape=(10, 5),
        grid=_GRID,
        x0=0.0,
        y0=0.0,
        dx=2.0,
        dy=2.0,
        png_data_uri='data:image/png;base64,abc',
    )


def test_build_plotly_figure_for_png_response() -> None:
    """PNG responses should become Plotly image traces."""
    response = _png_response()
    figure = build_plotly_figure(response)
    assert figure['data'][0]['type'] == 'image'
    assert figure['data'][0]['source'] == 'data:image/png;base64,abc'
    assert figure.get('config', {}).get('doubleClick') is False
    assert figure.get('config', {}).get('scrollZoom') is True
    assert figure.get('config', {}).get('responsive') is True
    assert figure['layout'].get('autosize') is True
    assert figure['layout'].get('dragmode') == 'zoom'
    assert figure['layout']['yaxis'].get('scaleanchor') is False


def test_build_plotly_figure_heatmap_uses_builtin_greys_colorscale() -> None:
    """Heatmap must use a valid Plotly built-in name (``Greys``), not ``Gray``."""
    assert DEFAULT_HEATMAP_COLORSCALE == 'Greys'


def test_build_plotly_figure_for_heatmap_response() -> None:
    """Heatmap responses should become Plotly heatmap traces."""
    response = RenderResponse(
        mode='heatmap_z',
        level=0,
        bounds=RowColBounds(row_min=0.0, row_max=4.0, col_min=0.0, col_max=2.0),
        shape=(4, 2),
        grid=_GRID,
        x0=0.0,
        y0=0.0,
        dx=1.0,
        dy=1.0,
        z=np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32),
        zmin=1.0,
        zmax=4.0,
    )
    figure = build_plotly_figure(response)
    assert figure['data'][0]['type'] == 'heatmap'
    assert figure['data'][0]['z'] == [[1.0, 2.0], [3.0, 4.0]]
    assert figure['data'][0]['colorscale'] == 'Greys'
    assert figure['data'][0].get('showscale') is False


def test_build_plotly_figure_heatmap_accepts_colorscale_override() -> None:
    """Optional ``heatmap_colorscale`` should override the default."""
    response = RenderResponse(
        mode='heatmap_z',
        level=0,
        bounds=RowColBounds(row_min=0.0, row_max=2.0, col_min=0.0, col_max=2.0),
        shape=(2, 2),
        grid=_GRID,
        x0=0.0,
        y0=0.0,
        dx=1.0,
        dy=1.0,
        z=np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.float32),
        zmin=0.0,
        zmax=1.0,
    )
    figure = build_plotly_figure(response, heatmap_colorscale='Viridis')
    assert figure['data'][0]['colorscale'] == 'Viridis'


def test_parse_relayout_payload_reads_axis_ranges() -> None:
    """Relayout payload should convert plot coordinates into row/column bounds."""
    payload = PlotlyViewportPayload(
        relayout={
            'xaxis.range[0]': 10,
            'xaxis.range[1]': 20,
            'yaxis.range[0]': 50,
            'yaxis.range[1]': 30,
        },
        width_px=800,
        height_px=600,
    )
    fallback = RowColBounds(row_min=0.0, row_max=60.0, col_min=0.0, col_max=100.0)
    transform = PlotlyCoordTransform(nrows=60, ncols=100, grid=_GRID)
    request = parse_relayout_payload(payload, transform, fallback)
    b = request.bounds
    assert (b.row_min, b.row_max, b.col_min, b.col_max) == (10.0, 20.0, 30.0, 50.0)
    assert request.viewport.width_px == 800
    assert request.viewport.height_px == 600


def test_parse_relayout_payload_reads_compound_axis_range_keys() -> None:
    """Plotly may send ``xaxis.range`` / ``yaxis.range`` as two-element lists."""
    payload = PlotlyViewportPayload(
        relayout={'xaxis.range': [0, 1], 'yaxis.range': [1, 0]},
        width_px=400,
        height_px=300,
    )
    fallback = RowColBounds(row_min=0.0, row_max=1.0, col_min=0.0, col_max=1.0)
    transform = PlotlyCoordTransform(nrows=100, ncols=100, grid=_GRID)
    request = parse_relayout_payload(payload, transform, fallback)
    b = request.bounds
    assert (b.row_min, b.row_max, b.col_min, b.col_max) == (0.0, 1.0, 0.0, 1.0)
    assert request.viewport.width_px == 400


def test_parse_relayout_payload_falls_back_for_partial_updates() -> None:
    """Missing relayout keys should use fallback-derived plot extents."""
    payload = PlotlyViewportPayload(relayout={}, width_px=500, height_px=250)
    fallback = RowColBounds(row_min=1.0, row_max=9.0, col_min=2.0, col_max=6.0)
    transform = PlotlyCoordTransform(nrows=20, ncols=20, grid=_GRID)
    request = parse_relayout_payload(payload, transform, fallback)
    b = request.bounds
    assert (b.row_min, b.row_max, b.col_min, b.col_max) == (1.0, 9.0, 2.0, 6.0)
