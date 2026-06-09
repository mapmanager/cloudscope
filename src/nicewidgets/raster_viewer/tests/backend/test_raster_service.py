"""Tests for the raster view service."""

from __future__ import annotations

import base64
import io

import numpy as np
from PIL import Image

from nicewidgets.raster_viewer.backend.image_model import RasterDisplayStyle, RowColBounds, ViewRequest, ViewportSize
from nicewidgets.raster_viewer.backend.raster_service import RasterViewService


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


def test_full_image_png_default_uses_coarse_overview(raster_service: RasterViewService) -> None:
    """Without a pixel budget, the overview uses the conservative coarse level."""
    response = raster_service.full_image_png()
    # Fixture pyramid (8x16) has 4 levels; coarse overview is min(num_levels-1, 3).
    assert response.level == 3


def test_full_image_png_max_pixels_selects_finest_fitting_level(
    raster_service: RasterViewService,
) -> None:
    """A generous budget selects the finest (full-resolution) level."""
    response = raster_service.full_image_png(max_pixels=8 * 16)
    assert response.level == 0


def test_full_image_png_max_pixels_steps_to_coarser_level(
    raster_service: RasterViewService,
) -> None:
    """A tight budget selects the finest level whose size fits the budget."""
    # Level 0 = 128 px (too big), level 1 = 4x8 = 32 px (fits first).
    response = raster_service.full_image_png(max_pixels=40)
    assert response.level == 1


def test_full_image_png_max_pixels_too_small_uses_coarsest_level(
    raster_service: RasterViewService,
) -> None:
    """When no level fits the budget, the coarsest level is used."""
    response = raster_service.full_image_png(max_pixels=1)
    assert response.level == raster_service.pyramid.num_levels - 1


def test_full_image_png_explicit_level_overrides_max_pixels(
    raster_service: RasterViewService,
) -> None:
    """An explicit ``level`` takes precedence over ``max_pixels``."""
    response = raster_service.full_image_png(level=2, max_pixels=8 * 16)
    assert response.level == 2


def _decode_png_rgb(data_uri: str) -> np.ndarray:
    """Decode a PNG data URI into an RGB ndarray ``(rows, cols, 3)``."""
    raw = base64.b64decode(data_uri.split(',', 1)[1])
    with Image.open(io.BytesIO(raw)) as im:
        return np.asarray(im.convert('RGB'))


def test_png_greys_matches_plotly_js_direction() -> None:
    """``Greys`` PNG must map low->dark, high->bright to match the Plotly.js heatmap."""
    arr = np.array([[0.0, 255.0]], dtype=np.float32)  # low | high
    style = RasterDisplayStyle(colorscale='Greys', zmin=0.0, zmax=255.0)
    rgb = _decode_png_rgb(RasterViewService.array_to_png_data_uri(arr, style=style))
    low, high = rgb[0, 0], rgb[0, 1]
    assert int(low.mean()) < int(high.mean())
    np.testing.assert_array_equal(low, (0, 0, 0))
    np.testing.assert_array_equal(high, (255, 255, 255))


def test_png_explicit_inverted_grays_unaffected() -> None:
    """Explicit stop lists are read literally; the reversal fix must not touch them."""
    arr = np.array([[0.0, 255.0]], dtype=np.float32)
    inverted = [[0, 'rgb(255,255,255)'], [1, 'rgb(0,0,0)']]
    style = RasterDisplayStyle(colorscale=inverted, zmin=0.0, zmax=255.0)
    rgb = _decode_png_rgb(RasterViewService.array_to_png_data_uri(arr, style=style))
    np.testing.assert_array_equal(rgb[0, 0], (255, 255, 255))
    np.testing.assert_array_equal(rgb[0, 1], (0, 0, 0))


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
