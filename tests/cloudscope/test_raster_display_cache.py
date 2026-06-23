"""Tests for ``RasterDisplayCache``."""

from __future__ import annotations

import numpy as np
import pytest

from cloudscope.raster_display_cache import (
    DEFAULT_RASTER_DISPLAY_CACHE_MAX_ENTRIES,
    RasterDisplayCache,
    RasterDisplayCacheKey,
    RasterDisplayPlaneKind,
    resolve_raster_display_cache_max_entries,
)


def test_resolve_raster_display_cache_max_entries_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('CLOUDSCOPE_RASTER_DISPLAY_CACHE_MAX_ENTRIES', raising=False)
    assert resolve_raster_display_cache_max_entries() == DEFAULT_RASTER_DISPLAY_CACHE_MAX_ENTRIES


def test_resolve_raster_display_cache_max_entries_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('CLOUDSCOPE_RASTER_DISPLAY_CACHE_MAX_ENTRIES', '5')
    assert resolve_raster_display_cache_max_entries() == 5


def test_resolve_raster_display_cache_max_entries_clamps_to_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('CLOUDSCOPE_RASTER_DISPLAY_CACHE_MAX_ENTRIES', '0')
    assert resolve_raster_display_cache_max_entries() == 1


def test_get_or_build_reuses_pyramid_on_hit() -> None:
    cache = RasterDisplayCache(max_entries=2)
    key = RasterDisplayCacheKey('file-a', 0, RasterDisplayPlaneKind.PRIMARY)
    loads = {'count': 0}

    def loader() -> np.ndarray:
        loads['count'] += 1
        return np.arange(12, dtype=np.float32).reshape(3, 4)

    entry_1 = cache.get_or_build(key, plane_loader=loader)
    entry_2 = cache.get_or_build(key, plane_loader=loader)

    assert loads['count'] == 1
    assert entry_2.pyramid is entry_1.pyramid
    assert entry_2.plane is entry_1.plane


def test_lru_evicts_oldest_entry() -> None:
    cache = RasterDisplayCache(max_entries=2)
    keys = [
        RasterDisplayCacheKey('a', 0, RasterDisplayPlaneKind.PRIMARY),
        RasterDisplayCacheKey('b', 0, RasterDisplayPlaneKind.PRIMARY),
        RasterDisplayCacheKey('c', 0, RasterDisplayPlaneKind.PRIMARY),
    ]
    loads = {'count': 0}

    def loader() -> np.ndarray:
        loads['count'] += 1
        return np.ones((2, 2), dtype=np.float32)

    for key in keys:
        cache.get_or_build(key, plane_loader=loader)

    assert loads['count'] == 3
    assert len(cache) == 2

    cache.get_or_build(keys[0], plane_loader=loader)
    assert loads['count'] == 4


def test_primary_and_reference_planes_are_distinct() -> None:
    cache = RasterDisplayCache(max_entries=2)
    primary_key = RasterDisplayCacheKey('file-a', 1, RasterDisplayPlaneKind.PRIMARY)
    reference_key = RasterDisplayCacheKey('file-a', 1, RasterDisplayPlaneKind.REFERENCE)

    primary = cache.get_or_build(
        primary_key,
        plane_loader=lambda: np.full((2, 2), 1.0, dtype=np.float32),
    )
    reference = cache.get_or_build(
        reference_key,
        plane_loader=lambda: np.full((2, 2), 2.0, dtype=np.float32),
    )

    assert primary.pyramid is not reference.pyramid
    assert float(primary.plane[0, 0]) == 1.0
    assert float(reference.plane[0, 0]) == 2.0


def test_invalidate_file_removes_matching_entries() -> None:
    cache = RasterDisplayCache(max_entries=3)
    cache.get_or_build(
        RasterDisplayCacheKey('a', 0, RasterDisplayPlaneKind.PRIMARY),
        plane_loader=lambda: np.ones((2, 2), dtype=np.float32),
    )
    cache.get_or_build(
        RasterDisplayCacheKey('b', 0, RasterDisplayPlaneKind.PRIMARY),
        plane_loader=lambda: np.ones((2, 2), dtype=np.float32),
    )

    cache.invalidate_file('a')

    assert len(cache) == 1


def test_load_primary_display_payload_uses_cache() -> None:
    from cloudscope.raster_display_cache import RasterDisplayCache
    from cloudscope.views.primary_image_view import _load_primary_display_payload

    class _Images:
        def __init__(self, plane: np.ndarray, header: object) -> None:
            self._plane = plane
            self.header = header

        def get_slice_data(self, channel: int) -> np.ndarray:
            assert channel == 0
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

    cache = RasterDisplayCache(max_entries=2)
    plane = np.arange(6, dtype=np.float32).reshape(2, 3)
    acq_image = _AcqImage(plane)

    _, _, pyramid_1, is_placeholder_1 = _load_primary_display_payload('f1', acq_image, 0, cache)
    _, _, pyramid_2, is_placeholder_2 = _load_primary_display_payload('f1', acq_image, 0, cache)

    assert is_placeholder_1 is False
    assert is_placeholder_2 is False
    assert pyramid_1 is not None
    assert pyramid_2 is pyramid_1
