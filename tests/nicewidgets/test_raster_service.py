"""Tests for RasterViewService rendering policy."""

from __future__ import annotations

import numpy as np

from nicewidgets.raster_viewer.backend.image_model import (
    BackendImage,
    RasterDisplayStyle,
    RasterGridSpec,
    RowColBounds,
    ViewRequest,
    ViewportSize,
)
from nicewidgets.raster_viewer.backend.pyramid import ImagePyramid
from nicewidgets.raster_viewer.backend.raster_service import RasterViewService


def _service(*, shape: tuple[int, int] = (32, 64), heatmap_max_values: int = 500_000) -> RasterViewService:
    """Build a small RasterViewService for tests."""
    rng = np.random.default_rng(0)
    data = rng.random(shape, dtype=np.float32)
    grid = RasterGridSpec(dx=0.5, dy=0.25, x_unit="row", y_unit="col")
    source = BackendImage(data=data, grid=grid)
    pyramid = ImagePyramid(source)
    return RasterViewService(source=source, pyramid=pyramid, heatmap_max_values=heatmap_max_values)


# ---- normalize_to_uint8 ----


def test_normalize_to_uint8_empty_returns_zeros() -> None:
    """Empty input should return a zero-shaped uint8 array."""
    arr = np.zeros((0, 0), dtype=np.float32)
    out = RasterViewService.normalize_to_uint8(arr)

    assert out.shape == (0, 0)
    assert out.dtype == np.uint8


def test_normalize_to_uint8_handles_nan_array() -> None:
    """An all-NaN input should return zeros without raising."""
    arr = np.full((3, 3), np.nan, dtype=np.float32)
    out = RasterViewService.normalize_to_uint8(arr)

    assert out.dtype == np.uint8
    assert (out == 0).all()


def test_normalize_to_uint8_handles_constant_array() -> None:
    """A constant input where hi <= lo should return zeros."""
    arr = np.full((4, 4), 5.0, dtype=np.float32)
    out = RasterViewService.normalize_to_uint8(arr)

    assert (out == 0).all()


def test_normalize_to_uint8_scales_range_to_uint8() -> None:
    """A linear array should map to 0..255 in uint8."""
    arr = np.array([[0.0, 0.5, 1.0]], dtype=np.float32)
    out = RasterViewService.normalize_to_uint8(arr)

    assert out[0, 0] == 0
    assert out[0, -1] == 255
    assert 110 <= out[0, 1] <= 135


# ---- array_to_png_data_uri ----


def test_array_to_png_data_uri_returns_png_prefix() -> None:
    """Output should start with the PNG data URI prefix."""
    arr = np.array([[0.0, 1.0], [2.0, 3.0]], dtype=np.float32)
    uri = RasterViewService.array_to_png_data_uri(arr, style=RasterDisplayStyle())

    assert uri.startswith("data:image/png;base64,")


def test_array_to_png_data_uri_handles_empty() -> None:
    """An empty array should still produce a valid 1x1 PNG."""
    arr = np.zeros((0, 0), dtype=np.float32)
    uri = RasterViewService.array_to_png_data_uri(arr, style=RasterDisplayStyle())

    assert uri.startswith("data:image/png;base64,")


def test_array_to_png_data_uri_handles_all_nan() -> None:
    """All-NaN array should produce a valid PNG (zeroed)."""
    arr = np.full((4, 4), np.nan, dtype=np.float32)
    uri = RasterViewService.array_to_png_data_uri(arr, style=RasterDisplayStyle())

    assert uri.startswith("data:image/png;base64,")


def test_array_to_png_data_uri_uses_provided_zmin_zmax() -> None:
    """Providing explicit zmin/zmax should not raise and should produce a PNG."""
    arr = np.array([[0.0, 1.0], [2.0, 3.0]], dtype=np.float32)
    style = RasterDisplayStyle(colorscale="Viridis", zmin=0.0, zmax=3.0)
    uri = RasterViewService.array_to_png_data_uri(arr, style=style)

    assert uri.startswith("data:image/png;base64,")


# ---- to_png_data_uri (grayscale) ----


def test_to_png_data_uri_returns_png_prefix() -> None:
    """Legacy grayscale PNG path should also return PNG data URI."""
    arr = np.array([[0.0, 1.0], [2.0, 3.0]], dtype=np.float32)
    uri = RasterViewService.to_png_data_uri(arr)

    assert uri.startswith("data:image/png;base64,")


# ---- choose_level ----


def test_choose_level_picks_level_zero_for_full_resolution_viewport() -> None:
    """Visible rows ~= viewport width should map to level 0."""
    svc = _service(shape=(64, 64))
    request = ViewRequest(
        bounds=RowColBounds(row_min=0, row_max=64, col_min=0, col_max=64),
        viewport=ViewportSize(width_px=64, height_px=64),
    )

    assert svc.choose_level(request) == 0


def test_choose_level_picks_coarser_level_for_small_viewport() -> None:
    """A small viewport relative to large bounds should pick a coarser level."""
    svc = _service(shape=(256, 256))
    request = ViewRequest(
        bounds=RowColBounds(row_min=0, row_max=256, col_min=0, col_max=256),
        viewport=ViewportSize(width_px=16, height_px=16),
    )

    level = svc.choose_level(request)
    assert level >= 1


# ---- choose_mode ----


def test_choose_mode_returns_heatmap_for_small_clip() -> None:
    """A small clip should default to heatmap_z."""
    svc = _service(shape=(8, 8))
    request = ViewRequest(
        bounds=RowColBounds(row_min=0, row_max=8, col_min=0, col_max=8),
        viewport=ViewportSize(width_px=200, height_px=200),
    )
    clip = np.zeros((8, 8), dtype=np.float32)

    assert svc.choose_mode(request, clip) == "heatmap_z"


def test_choose_mode_returns_png_for_large_clip() -> None:
    """A clip with more values than the threshold should choose image_png."""
    svc = _service(shape=(64, 64), heatmap_max_values=16)
    request = ViewRequest(
        bounds=RowColBounds(row_min=0, row_max=64, col_min=0, col_max=64),
        viewport=ViewportSize(width_px=64, height_px=64),
    )
    clip = np.zeros((10, 10), dtype=np.float32)

    assert svc.choose_mode(request, clip) == "image_png"


def test_choose_mode_respects_prefer_mode_override() -> None:
    """A request with prefer_mode should be honored."""
    svc = _service()
    request = ViewRequest(
        bounds=RowColBounds(row_min=0, row_max=8, col_min=0, col_max=8),
        viewport=ViewportSize(width_px=100, height_px=100),
        prefer_mode="image_png",
    )
    clip = np.zeros((2, 2), dtype=np.float32)

    assert svc.choose_mode(request, clip) == "image_png"


# ---- render ----


def test_render_returns_heatmap_response_with_z_array() -> None:
    """A small viewport should yield a heatmap_z response."""
    svc = _service(shape=(8, 8))
    request = ViewRequest(
        bounds=RowColBounds(row_min=0, row_max=8, col_min=0, col_max=8),
        viewport=ViewportSize(width_px=200, height_px=200),
    )

    response = svc.render(request)

    assert response.mode == "heatmap_z"
    assert response.z is not None
    assert response.z.shape == (8, 8)
    assert response.png_data_uri is None


def test_render_returns_png_response_with_uri() -> None:
    """A request with image_png prefer mode should return a PNG."""
    svc = _service(shape=(8, 8))
    request = ViewRequest(
        bounds=RowColBounds(row_min=0, row_max=8, col_min=0, col_max=8),
        viewport=ViewportSize(width_px=200, height_px=200),
        prefer_mode="image_png",
    )

    response = svc.render(request)

    assert response.mode == "image_png"
    assert response.z is None
    assert response.png_data_uri is not None
    assert response.png_data_uri.startswith("data:image/png;base64,")


def test_render_uses_display_style_zmin_zmax_when_provided() -> None:
    """Explicit zmin/zmax in display style should be propagated to the response."""
    svc = _service(shape=(8, 8))
    request = ViewRequest(
        bounds=RowColBounds(row_min=0, row_max=8, col_min=0, col_max=8),
        viewport=ViewportSize(width_px=200, height_px=200),
    )

    style = RasterDisplayStyle(zmin=0.1, zmax=0.9)
    response = svc.render(request, display_style=style)

    assert response.zmin == 0.1
    assert response.zmax == 0.9


def test_render_clips_to_source_shape() -> None:
    """Bounds outside the source shape should be clipped to the source size."""
    svc = _service(shape=(8, 8))
    request = ViewRequest(
        bounds=RowColBounds(row_min=-10, row_max=100, col_min=-5, col_max=100),
        viewport=ViewportSize(width_px=200, height_px=200),
        prefer_mode="image_png",
    )

    response = svc.render(request)

    assert response.bounds.row_min == 0.0
    assert response.bounds.row_max == 8.0
    assert response.bounds.col_min == 0.0
    assert response.bounds.col_max == 8.0


# ---- full_image_png ----


def test_full_image_png_returns_png_for_default_level() -> None:
    """`full_image_png` should always return a PNG response."""
    svc = _service(shape=(16, 16))

    response = svc.full_image_png()

    assert response.mode == "image_png"
    assert response.png_data_uri is not None
    assert response.bounds.row_max == 16.0
    assert response.bounds.col_max == 16.0


def test_full_image_png_respects_explicit_level() -> None:
    """An explicit level should be used to compute downsample / shape."""
    svc = _service(shape=(32, 32))
    response = svc.full_image_png(level=0)

    assert response.level == 0
    assert response.dx == svc.grid.dx
    assert response.dy == svc.grid.dy


def test_full_image_png_uses_display_style() -> None:
    """A custom display style should not raise and should produce a PNG."""
    svc = _service(shape=(16, 16))
    response = svc.full_image_png(display_style=RasterDisplayStyle(colorscale="Viridis"))

    assert response.png_data_uri is not None


# ---- property accessors ----


def test_service_exposes_source_pyramid_grid() -> None:
    """Service should expose its source, pyramid, and grid via properties."""
    svc = _service(shape=(8, 8))

    assert isinstance(svc.source, BackendImage)
    assert isinstance(svc.pyramid, ImagePyramid)
    assert svc.grid.dx > 0
