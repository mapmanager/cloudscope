"""Tests for ReferenceImageView helpers."""

from __future__ import annotations

import numpy as np

from acqstore.acq_image.file_loaders.base_file_loader import ReferenceImage
from cloudscope.event_bus import EventBus
from cloudscope.views.base_view import BaseView
from cloudscope.views.reference_image_view import (
    ReferenceImageView,
    _load_reference_plane_payload,
    raster_grid_spec_from_reference_plane,
)
from cloudscope.views.view_ids import ViewId


class _Images:
    """Small image-loader stand-in for ReferenceImageView tests."""

    def __init__(self, reference_image: ReferenceImage | None) -> None:
        """Create the fake images object.

        Args:
            reference_image: Reference image to expose.
        """
        self.reference_image = reference_image


class _AcqImage:
    """Small AcqImage stand-in for ReferenceImageView tests."""

    def __init__(self, reference_image: ReferenceImage | None) -> None:
        """Create the fake acquisition image.

        Args:
            reference_image: Reference image to expose through ``images``.
        """
        self.images = _Images(reference_image)


def _reference_image() -> ReferenceImage:
    """Return a simple two-dimensional reference image.

    Returns:
        Reference image with Y/X calibration.
    """
    return ReferenceImage(
        array=np.arange(6, dtype=np.uint16).reshape(2, 3),
        dims=("Y", "X"),
        num_channels=1,
        line_roi=None,
        coord_units=(("Y", "um"), ("X", "um")),
        coord_scales=(("Y", 0.5), ("X", 0.25)),
        coords=(),
    )


def test_reference_image_view_is_base_view_and_display_only() -> None:
    """ReferenceImageView should be a display-only BaseView."""
    view = ReferenceImageView(EventBus())

    assert isinstance(view, BaseView)
    assert view.view_id is ViewId.REFERENCE_IMAGE
    assert view.disable_when_busy is False


def test_reference_image_payload_without_file_returns_placeholder() -> None:
    """Missing file selection returns a placeholder payload."""
    array, grid, message = _load_reference_plane_payload(None, None, None)

    assert array.shape == (2, 2)
    assert grid.dx == 1.0
    assert "No file" in message


def test_reference_image_payload_without_reference_returns_placeholder() -> None:
    """AcqImages without reference images return a placeholder payload."""
    array, grid, message = _load_reference_plane_payload("file", _AcqImage(None), 0)

    assert array.shape == (2, 2)
    assert grid.dx == 1.0
    assert "No reference" in message


def test_reference_image_payload_uses_acqstore_plane_api() -> None:
    """ReferenceImageView payload loading delegates display logic to AcqStore."""
    array, grid, message = _load_reference_plane_payload("file", _AcqImage(_reference_image()), 0)

    np.testing.assert_array_equal(array, np.arange(6, dtype=np.uint16).reshape(2, 3))
    assert grid.dx == 0.5
    assert grid.dy == 0.25
    assert grid.x_unit == "um"
    assert grid.y_unit == "um"
    assert message == "Reference image"


def test_raster_grid_spec_from_reference_plane() -> None:
    """Reference image plane calibration maps directly to raster grid."""
    plane = _reference_image().get_plane(0)
    grid = raster_grid_spec_from_reference_plane(plane)

    assert grid.dx == plane.dx
    assert grid.dy == plane.dy
    assert grid.x_unit == plane.x_unit
    assert grid.y_unit == plane.y_unit
