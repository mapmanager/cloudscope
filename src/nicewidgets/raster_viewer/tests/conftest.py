"""Shared pytest fixtures."""

from __future__ import annotations

import numpy as np
import pytest

from nicewidgets.raster_viewer.backend.image_model import BackendImage, RasterGridSpec
from nicewidgets.raster_viewer.backend.pyramid import ImagePyramid
from nicewidgets.raster_viewer.backend.raster_service import RasterViewService

_DEFAULT_GRID = RasterGridSpec(dx=1.0, dy=1.0, x_unit='', y_unit='')


@pytest.fixture()
def sample_array() -> np.ndarray:
    """Return a small deterministic 2D array for tests."""
    return np.arange(8 * 16, dtype=np.float32).reshape(8, 16)


@pytest.fixture()
def backend_image(sample_array: np.ndarray) -> BackendImage:
    """Return a backend image fixture."""
    return BackendImage(sample_array, grid=_DEFAULT_GRID)


@pytest.fixture()
def image_pyramid(backend_image: BackendImage) -> ImagePyramid:
    """Return an image pyramid fixture."""
    return ImagePyramid(backend_image)


@pytest.fixture()
def raster_service(backend_image: BackendImage, image_pyramid: ImagePyramid) -> RasterViewService:
    """Return a raster service fixture."""
    return RasterViewService(backend_image, image_pyramid, heatmap_max_values=20)
