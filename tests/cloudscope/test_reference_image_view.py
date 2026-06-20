"""Tests for ReferenceImageView helpers."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from acqstore.acq_image.file_loaders.base_file_loader import ReferenceImage
from cloudscope.event_bus import EventBus
from cloudscope.state import PrimarySelection
from cloudscope.views.base_view import BaseView
from cloudscope.views.reference_image_view import (
    ReferenceImageView,
    _load_reference_plane_payload,
    raster_grid_spec_from_reference_plane,
    reference_contrast_window,
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


class _FakeAcqImageList:
    """Fake acquisition image list keyed by file id."""

    def __init__(self, images: dict[str, object]) -> None:
        self._images = dict(images)

    def get_file_by_id(self, file_id: str | None) -> object | None:
        """Return the image registered for ``file_id`` if present."""
        return self._images.get(file_id)


class _FakeAppState:
    """Fake page state exposing a primary selection and image list."""

    def __init__(self, selection: PrimarySelection, acq_image_list: _FakeAcqImageList) -> None:
        self.selection = selection
        self.acq_image_list = acq_image_list


def test_reference_image_view_resyncs_selection_from_app_state_on_show() -> None:
    """Showing a hidden view should resync selection from app_state, not stale cache."""
    image_a = _AcqImage(None)
    image_b = _AcqImage(_reference_image())
    app_state = _FakeAppState(
        selection=PrimarySelection(file_id="b", channel=1, roi_id=2),
        acq_image_list=_FakeAcqImageList({"a": image_a, "b": image_b}),
    )
    view = ReferenceImageView(EventBus(), app_state=app_state, initially_visible=False)
    refreshed: list[str | None] = []
    view._refresh_reference_from_current_selection = (
        lambda *, force: refreshed.append(view.current_selection.file_id)
    )

    view.on_show()

    assert view.current_selection.file_id == "b"
    assert view.current_selection.channel == 1
    assert view.current_acq_image is image_b
    assert refreshed and refreshed[-1] == "b"


def test_reference_image_payload_without_file_returns_empty() -> None:
    """Missing file selection returns no reference plane."""
    array, grid, message, is_real = _load_reference_plane_payload(None, None, None)

    assert array is None
    assert grid is None
    assert is_real is False
    assert "No file" in message


def test_reference_image_payload_without_reference_returns_empty() -> None:
    """AcqImages without reference images return no reference plane."""
    array, grid, message, is_real = _load_reference_plane_payload("file", _AcqImage(None), 0)

    assert array is None
    assert grid is None
    assert is_real is False
    assert "No reference" in message


def test_reference_image_payload_uses_acqstore_plane_api() -> None:
    """ReferenceImageView payload loading delegates display logic to AcqStore."""
    array, grid, message, is_real = _load_reference_plane_payload(
        "file", _AcqImage(_reference_image()), 0
    )

    assert is_real is True
    assert array is not None
    assert grid is not None
    np.testing.assert_array_equal(array, np.arange(6, dtype=np.uint16).reshape(2, 3))
    assert grid.dx == 0.5
    assert grid.dy == 0.25
    assert grid.x_unit == "um"
    assert grid.y_unit == "um"
    assert message == "Reference image"


def test_refresh_reference_async_clears_viewer_when_no_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Switching to a file without a reference image clears the raster viewer."""
    async def _direct_io_bound(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    import cloudscope.views.reference_image_view as reference_image_view_module

    monkeypatch.setattr(reference_image_view_module.run, 'io_bound', _direct_io_bound)

    view = ReferenceImageView(EventBus())
    view._viewer = MagicMock()
    view._viewer.clear_data = AsyncMock()
    view._viewer.set_data = AsyncMock()

    asyncio.run(view._refresh_reference_async("file", _AcqImage(None), 0))

    view._viewer.clear_data.assert_awaited_once()
    view._viewer.set_data.assert_not_awaited()


def test_refresh_reference_async_set_data_when_reference_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A file with a reference image loads data into the raster viewer."""
    async def _direct_io_bound(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    import cloudscope.views.reference_image_view as reference_image_view_module

    monkeypatch.setattr(reference_image_view_module.run, 'io_bound', _direct_io_bound)

    view = ReferenceImageView(EventBus())
    view._viewer = MagicMock()
    view._viewer.clear_data = AsyncMock()
    view._viewer.set_data = AsyncMock()
    view._apply_reference_contrast = AsyncMock()

    asyncio.run(view._refresh_reference_async("file", _AcqImage(_reference_image()), 0))

    view._viewer.clear_data.assert_not_awaited()
    view._viewer.set_data.assert_awaited_once()
    view._apply_reference_contrast.assert_awaited_once()


def test_reference_contrast_window_uses_percentiles() -> None:
    """A non-degenerate plane yields a percentile (zmin, zmax) window."""
    plane = np.arange(100, dtype=np.uint16).reshape(10, 10)

    window = reference_contrast_window(plane)

    assert window is not None
    zmin, zmax = window
    assert isinstance(zmin, float)
    assert isinstance(zmax, float)
    assert zmin < zmax
    # Percentile clip (1.0 / 99.5) keeps the window inside the data extent.
    assert zmin >= 0.0
    assert zmax <= 99.0


def test_reference_contrast_window_empty_plane_returns_none() -> None:
    """An empty plane produces no window (viewer keeps auto-stretch)."""
    assert reference_contrast_window(np.empty((0, 0), dtype=np.uint16)) is None


def test_reference_contrast_window_flat_plane_returns_none() -> None:
    """A flat plane (placeholder) is degenerate and returns no window."""
    assert reference_contrast_window(np.zeros((2, 2), dtype=np.float32)) is None


def test_raster_grid_spec_from_reference_plane() -> None:
    """Reference image plane calibration maps directly to raster grid."""
    plane = _reference_image().get_plane(0)
    grid = raster_grid_spec_from_reference_plane(plane)

    assert grid.dx == plane.dx
    assert grid.dy == plane.dy
    assert grid.x_unit == plane.x_unit
    assert grid.y_unit == plane.y_unit
