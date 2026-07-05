"""LRU cache for raster display planes and prebuilt image pyramids."""

from __future__ import annotations

import os
import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

import numpy as np

from nicewidgets.raster_viewer.backend.image_model import BackendImage, RasterGridSpec
from nicewidgets.raster_viewer.backend.pyramid import ImagePyramid

# Default LRU cap for cloud deployments with limited memory. Override with
# ``CLOUDSCOPE_RASTER_DISPLAY_CACHE_MAX_ENTRIES`` (minimum 1).
DEFAULT_RASTER_DISPLAY_CACHE_MAX_ENTRIES = 20

# Grid used only when constructing ``BackendImage`` for pyramid build; pyramid
# math ignores calibration and uses raw array shape only.
_PYRAMID_BUILD_GRID = RasterGridSpec(dx=1.0, dy=1.0, x_unit='', y_unit='')


class RasterDisplayPlaneKind(str, Enum):
    """Distinguish primary slice planes from reference-image planes."""

    PRIMARY = 'primary'
    REFERENCE = 'reference'


@dataclass(frozen=True, slots=True)
class RasterDisplayCacheKey:
    """Cache key for one display plane within one file, channel, and slice."""

    file_id: str
    channel: int
    z: int
    t: int
    kind: RasterDisplayPlaneKind


@dataclass(slots=True)
class RasterDisplayEntry:
    """Cached plane array and its prebuilt pyramid."""

    plane: np.ndarray
    pyramid: ImagePyramid


def resolve_raster_display_cache_max_entries() -> int:
    """Resolve the LRU capacity from the environment or factory default.

    Returns:
        Maximum number of cached ``(file_id, channel, z, t, kind)`` entries, at least 1.
    """
    raw = os.environ.get('CLOUDSCOPE_RASTER_DISPLAY_CACHE_MAX_ENTRIES', '').strip()
    if not raw:
        return DEFAULT_RASTER_DISPLAY_CACHE_MAX_ENTRIES
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_RASTER_DISPLAY_CACHE_MAX_ENTRIES
    return max(1, value)


class RasterDisplayCache:
    """Process-local LRU cache of raster planes and display pyramids.

    Pyramid levels depend only on pixel array shape and values. Physical
    calibration (``RasterGridSpec``) is applied when constructing a fresh
    :class:`~nicewidgets.raster_viewer.backend.raster_service.RasterViewService`
    for display; it does not require rebuilding the cached pyramid.
    """

    def __init__(self, *, max_entries: int | None = None) -> None:
        """Create an empty cache.

        Args:
            max_entries: LRU capacity. When ``None``, uses
                :func:`resolve_raster_display_cache_max_entries`.
        """
        resolved = max_entries if max_entries is not None else resolve_raster_display_cache_max_entries()
        self._max_entries = max(1, int(resolved))
        self._entries: OrderedDict[RasterDisplayCacheKey, RasterDisplayEntry] = OrderedDict()
        self._lock = threading.Lock()

    @property
    def max_entries(self) -> int:
        """Return the configured LRU capacity."""
        return self._max_entries

    def __len__(self) -> int:
        """Return the number of cached entries."""
        with self._lock:
            return len(self._entries)

    def get_or_build(
        self,
        key: RasterDisplayCacheKey,
        *,
        plane_loader: Callable[[], np.ndarray],
    ) -> RasterDisplayEntry:
        """Return a cached entry or load the plane and build a pyramid on miss.

        Args:
            key: File, channel, ``z``/``t`` slice indices, and plane kind.
            plane_loader: Callable that returns a 2D ``(Y, X)`` array. Invoked
                only on cache miss.

        Returns:
            Cached or newly built display entry.

        Raises:
            ValueError: If ``plane_loader`` returns a non-2D array.
        """
        with self._lock:
            existing = self._entries.get(key)
            if existing is not None:
                self._entries.move_to_end(key)
                return existing

        plane = np.asarray(plane_loader())
        if plane.ndim != 2:
            raise ValueError(f'Expected 2D plane (Y, X), got shape={plane.shape}')

        source = BackendImage(plane, grid=_PYRAMID_BUILD_GRID)
        pyramid = ImagePyramid(source)
        entry = RasterDisplayEntry(plane=plane, pyramid=pyramid)

        with self._lock:
            cached = self._entries.get(key)
            if cached is not None:
                self._entries.move_to_end(key)
                return cached
            self._entries[key] = entry
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)
            return entry

    def invalidate_file(self, file_id: str) -> None:
        """Remove all cached entries for one file id.

        Args:
            file_id: Acquisition file identifier.

        Returns:
            None.
        """
        with self._lock:
            keys = [key for key in self._entries if key.file_id == file_id]
            for key in keys:
                del self._entries[key]

    def clear(self) -> None:
        """Remove all cached entries.

        Returns:
            None.
        """
        with self._lock:
            self._entries.clear()
