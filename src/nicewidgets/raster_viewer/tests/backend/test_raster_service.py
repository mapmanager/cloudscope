"""Tests for the raster view service."""

from __future__ import annotations

import base64
import io

import numpy as np
from PIL import Image

from raster_viewer.backend.image_model import RasterDisplayStyle, RowColBounds, ViewRequest, ViewportSize
from raster_viewer.backend.raster_service import RasterViewService


def test_choose_level_prefers_coarser_level_for_zoomed_out_view(raster_service: RasterViewService) -> None:
    """Zoomed-out views should prefer a coarser pyramid level.

    Plot-x spans rows and plot-y spans cols; density uses ``row_span/width_px``
    and ``col_span/height_px``. Match the previous test's target downsample (~4)
    with a slightly larger viewport than the old column-as-x mapping used.
    """
    request = ViewRequest(
        bounds=RowColBounds(row_min=0.0, row_max=8.0, col_min=0.0, col_max=16.0),
        viewport=ViewportSize(width_px=8, height_px=4),
    )
    level = raster_service.choose_level(request)
    assert level == 2


def test_choose_mode_prefers_heatmap_when_clip_is_small(raster_service: RasterViewService) -> None:
    """Small clips should stay numeric."""
    request = ViewRequest(
        bounds=RowColBounds(row_min=0.0, row_max=2.0, col_min=0.0, col_max=4.0),
        viewport=ViewportSize(width_px=400, height_px=200),
    )
    clip = np.zeros((2, 4), dtype=np.float32)
    assert raster_service.choose_mode(request, clip) == 'heatmap_z'


def test_choose_mode_prefers_png_when_clip_is_large(raster_service: RasterViewService) -> None:
    """Large clips should use PNG mode."""
    request = ViewRequest(
        bounds=RowColBounds(row_min=0.0, row_max=8.0, col_min=0.0, col_max=16.0),
        viewport=ViewportSize(width_px=400, height_px=200),
    )
    clip = np.zeros((10, 10), dtype=np.float32)
    assert raster_service.choose_mode(request, clip) == 'image_png'


def test_render_returns_heatmap_response_for_small_clip(raster_service: RasterViewService) -> None:
    """Service should return numeric heatmap data for small requests."""
    request = ViewRequest(
        bounds=RowColBounds(row_min=0.0, row_max=2.0, col_min=0.0, col_max=4.0),
        viewport=ViewportSize(width_px=400, height_px=200),
    )
    response = raster_service.render(request)
    assert response.mode == 'heatmap_z'
    assert response.z is not None
    assert response.png_data_uri is None


def test_render_returns_png_response_for_large_clip(raster_service: RasterViewService) -> None:
    """Service should return PNG data for large requests."""
    request = ViewRequest(
        bounds=RowColBounds(row_min=0.0, row_max=8.0, col_min=0.0, col_max=16.0),
        viewport=ViewportSize(width_px=400, height_px=200),
    )
    response = raster_service.render(request)
    assert response.mode == 'image_png'
    assert response.png_data_uri is not None
    assert response.z is None


def test_full_image_png_returns_data_uri(raster_service: RasterViewService) -> None:
    """Full-image overview should be encoded as a PNG data URI."""
    response = raster_service.full_image_png(level=0)
    assert response.mode == 'image_png'
    assert response.png_data_uri is not None
    assert response.png_data_uri.startswith('data:image/png;base64,')
    raw = base64.b64decode(response.png_data_uri.split(',', 1)[1])
    assert raw[:8] == b'\x89PNG\r\n\x1a\n'
    with Image.open(io.BytesIO(raw)) as im:
        assert im.mode == 'RGB'


def test_full_image_png_respects_display_style_colorscale(raster_service: RasterViewService) -> None:
    """Overview PNG should use Plotly colorsampling (RGB), not raw grayscale L."""
    style = RasterDisplayStyle(colorscale='Reds', zmin=0.0, zmax=255.0)
    response = raster_service.full_image_png(level=0, display_style=style)
    raw = base64.b64decode(response.png_data_uri.split(',', 1)[1])
    with Image.open(io.BytesIO(raw)) as im:
        assert im.mode == 'RGB'


def test_render_heatmap_uses_display_style_z_window(raster_service: RasterViewService) -> None:
    """Pinned z-range from :class:`RasterDisplayStyle` should appear on heatmap responses."""
    request = ViewRequest(
        bounds=RowColBounds(row_min=0.0, row_max=2.0, col_min=0.0, col_max=4.0),
        viewport=ViewportSize(width_px=400, height_px=200),
    )
    style = RasterDisplayStyle(zmin=-1.0, zmax=2.0)
    response = raster_service.render(request, display_style=style)
    assert response.mode == 'heatmap_z'
    assert response.zmin == -1.0
    assert response.zmax == 2.0


def test_normalize_to_uint8_handles_constant_input() -> None:
    """Constant arrays should normalize to zeros without error."""
    arr = np.ones((2, 2), dtype=np.float32)
    out = RasterViewService.normalize_to_uint8(arr)
    np.testing.assert_array_equal(out, np.zeros((2, 2), dtype=np.uint8))
