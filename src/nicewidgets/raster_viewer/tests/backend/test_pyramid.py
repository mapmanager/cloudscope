"""Tests for the image pyramid."""

from __future__ import annotations

import numpy as np

from nicewidgets.raster_viewer.backend.image_model import RowColBounds
from nicewidgets.raster_viewer.backend.pyramid import ImagePyramid


def test_pyramid_builds_expected_first_levels(image_pyramid: ImagePyramid) -> None:
    """Pyramid should build power-of-two downsample levels."""
    info = image_pyramid.level_info()
    assert info[0].downsample == 1
    assert info[0].shape == (8, 16)
    assert info[1].downsample == 2
    assert info[1].shape == (4, 8)
    assert info[2].downsample == 4
    assert info[2].shape == (2, 4)


def test_downsample2_averages_2x2_blocks() -> None:
    """Box downsample should average each 2x2 block."""
    data = np.array([[0, 2], [4, 6]], dtype=np.float32)
    out = ImagePyramid._downsample2(data)
    np.testing.assert_allclose(out, np.array([[3.0]], dtype=np.float32))


def test_clip_from_level_uses_source_coordinates(image_pyramid: ImagePyramid) -> None:
    """Level clips should map full-resolution row/col bounds through the downsample."""
    bounds = RowColBounds(row_min=2.0, row_max=6.0, col_min=4.0, col_max=12.0)
    clip = image_pyramid.clip_from_level(level=1, bounds=bounds)
    expected = image_pyramid.get_level(1)[1:3, 2:6]
    np.testing.assert_array_equal(clip, expected)
