"""Tests for primary image grid mapping and plane payload selection."""

from __future__ import annotations

import numpy as np
import pytest

from acqstore.acq_image.file_loaders.base_file_loader import ImageHeader

from cloudscope.views.primary_image_view import (
    _load_plane_payload,
    _placeholder_plane,
    raster_grid_spec_from_image_header,
)


def _minimal_header(
    *,
    dims: tuple[str, ...],
    shape: tuple[int, ...],
    sizes: dict[str, int],
    physical_units: tuple[float | None, ...],
    physical_units_labels: tuple[str, ...] = (),
) -> ImageHeader:
    labels = physical_units_labels if physical_units_labels else tuple('' for _ in physical_units)
    return ImageHeader(
        path='/tmp/test.oir',
        shape=shape,
        dims=dims,
        sizes=sizes,
        dtype=np.dtype('uint16'),
        num_channels=1,
        num_scenes=1,
        physical_units=physical_units,
        physical_units_labels=labels,
    )


def test_raster_grid_spec_from_image_header_maps_yx_steps_and_labels() -> None:
    h = _minimal_header(
        dims=('Y', 'X'),
        shape=(100, 200),
        sizes={'Y': 100, 'X': 200},
        physical_units=(0.4, 0.25),
        physical_units_labels=('space Y', 'space X'),
    )
    g = raster_grid_spec_from_image_header(h)
    assert g.dx == 0.4
    assert g.dy == 0.25
    assert g.x_unit == 'space Y'
    assert g.y_unit == 'space X'


def test_raster_grid_spec_raises_when_y_missing() -> None:
    h = _minimal_header(
        dims=('Z', 'X'),
        shape=(5, 10),
        sizes={'Z': 5, 'X': 10},
        physical_units=(1.0, 1.0),
    )
    with pytest.raises(ValueError, match='Y and X'):
        raster_grid_spec_from_image_header(h)


def test_raster_grid_spec_raises_on_nan_calibration() -> None:
    h = _minimal_header(
        dims=('Y', 'X'),
        shape=(10, 20),
        sizes={'Y': 10, 'X': 20},
        physical_units=(float('nan'), 1.0),
    )
    with pytest.raises(ValueError, match='calibration'):
        raster_grid_spec_from_image_header(h)


def test_load_plane_payload_placeholder_without_acq() -> None:
    plane, grid = _load_plane_payload('/x', None, 0)
    assert plane.shape == (2, 2)
    assert grid.dx == 1.0 and grid.dy == 1.0


def test_placeholder_plane_returns_float32() -> None:
    plane, _ = _placeholder_plane()
    assert plane.dtype == np.float32
