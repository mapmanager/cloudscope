"""Tests that PrimaryImageView refreshes from selection, not pixel events."""

from __future__ import annotations

import numpy as np

from cloudscope.event_bus import EventBus
from cloudscope.state import PrimarySelection
from cloudscope.views.primary_image_view import PrimaryImageView, _load_primary_display_payload


class _Images:
    def __init__(self, plane: np.ndarray, header: object) -> None:
        self._plane = plane
        self.header = header
        self.slice_calls = 0
        self.implicit_load_calls = 0

    def get_slice_data_loaded(self, channel: int, *, z: int = 0, t: int = 0) -> np.ndarray:
        self.slice_calls += 1
        assert channel == 0
        return self._plane

    def get_slice_data(self, channel: int) -> np.ndarray:
        self.implicit_load_calls += 1
        return self._plane


class _Header:
    dims = ('Y', 'X')

    def _physical_step_for_dim(self, dim: str) -> float:
        return 1.0

    def _physical_label_for_dim(self, dim: str) -> str:
        return dim


class _AcqImage:
    def __init__(self, plane: np.ndarray) -> None:
        self.images = _Images(plane, _Header())

    def pixels_loaded(self) -> bool:
        return True


def test_load_primary_display_payload_uses_loaded_slice_only() -> None:
    plane = np.arange(6, dtype=np.float32).reshape(2, 3)
    acq = _AcqImage(plane)
    result = _load_primary_display_payload('f1', acq, 0, None)
    assert result is not None
    assert acq.images.slice_calls == 1
    assert acq.images.implicit_load_calls == 0


def test_load_primary_display_payload_returns_none_without_selection() -> None:
    plane = np.arange(6, dtype=np.float32).reshape(2, 3)
    acq = _AcqImage(plane)
    assert _load_primary_display_payload(None, acq, 0, None) is None
    assert _load_primary_display_payload('f1', None, 0, None) is None
    assert _load_primary_display_payload('f1', acq, None, None) is None


def test_on_primary_selection_changed_triggers_refresh() -> None:
    bus = EventBus()
    view = PrimaryImageView(bus)
    calls: list[bool] = []
    view._sync_slice_sliders_from_header = lambda: None  # type: ignore[method-assign]
    view._refresh_raster_from_current_selection = lambda **kwargs: calls.append(  # type: ignore[method-assign]
        kwargs.get('include_overlays', True)
    )

    view.on_primary_selection_changed()

    assert calls == [True]
