"""Tests for core backend image models."""

from __future__ import annotations

import numpy as np
import pytest

from nicewidgets.raster_viewer.backend.image_model import BackendImage, RasterGridSpec, RowColBounds

_DEFAULT_GRID = RasterGridSpec(dx=1.0, dy=1.0, x_unit='', y_unit='')


def test_backend_image_rejects_non_2d() -> None:
    """BackendImage should reject non-2D arrays."""
    data = np.zeros((2, 3, 4), dtype=np.float32)
    with pytest.raises(ValueError, match='2D array'):
        BackendImage(data, grid=_DEFAULT_GRID)


def test_raster_grid_spec_rejects_non_positive_dx() -> None:
    """RasterGridSpec must reject non-positive spacing."""
    with pytest.raises(ValueError, match='positive'):
        RasterGridSpec(dx=0.0, dy=1.0, x_unit='', y_unit='')


def test_backend_image_shape_properties(backend_image: BackendImage) -> None:
    """Shape-derived properties should match the source array."""
    assert backend_image.shape == (8, 16)
    assert backend_image.height == 8
    assert backend_image.width == 16


def test_clip_returns_requested_region(backend_image: BackendImage) -> None:
    """Clip should return the requested row/column region."""
    bounds = RowColBounds(row_min=1.0, row_max=4.0, col_min=2.0, col_max=5.0)
    clip = backend_image.clip(bounds)
    np.testing.assert_array_equal(clip, backend_image.data[1:4, 2:5])


def test_clip_clamps_to_image_extent(backend_image: BackendImage) -> None:
    """Out-of-range bounds should be clipped to the image extent."""
    bounds = RowColBounds(row_min=-1.0, row_max=99.0, col_min=-5.0, col_max=20.0)
    clip = backend_image.clip(bounds)
    np.testing.assert_array_equal(clip, backend_image.data)
