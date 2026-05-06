"""Tests for CloudScope image-toolbar view helpers."""

from __future__ import annotations

from cloudscope.views.image_toolbar_view import (
    channel_options_for_acq_image,
    roi_options_for_acq_image,
)


class FakeImages:
    """Fake image helper exposing channel indices."""

    @property
    def channel_indices(self) -> list[int]:
        """Return fake channel indices."""
        return [0, 1, 2]


class FakeRois:
    """Fake ROI helper exposing integer ROI identifiers."""

    def get_roi_ids(self) -> list[int]:
        """Return fake ROI identifiers."""
        return [10, 20]


class FakeAcqImage:
    """Fake acquisition image for toolbar helper tests."""

    @property
    def images(self) -> FakeImages:
        """Return fake image helper."""
        return FakeImages()

    @property
    def rois(self) -> FakeRois:
        """Return fake ROI helper."""
        return FakeRois()


def test_channel_options_for_acq_image_returns_string_options() -> None:
    """Toolbar channel options should be strings expected by ImageToolbarWidget."""
    assert channel_options_for_acq_image(FakeAcqImage()) == ["0", "1", "2"]


def test_roi_options_for_acq_image_returns_int_options() -> None:
    """Toolbar ROI options should remain integer backend ROI ids."""
    assert roi_options_for_acq_image(FakeAcqImage()) == [10, 20]

from cloudscope.event_bus import EventBus
from cloudscope.views.base_view import BaseView
from cloudscope.views.image_toolbar_view import ImageToolbarView
from cloudscope.views.view_ids import ViewId


def test_image_toolbar_view_is_base_view() -> None:
    """ImageToolbarView should participate in BaseView lifecycle."""
    view = ImageToolbarView(event_bus=EventBus())

    assert isinstance(view, BaseView)
    assert view.view_id is ViewId.IMAGE_TOOLBAR
    assert view.disable_when_busy is True
