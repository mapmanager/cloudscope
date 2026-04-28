from contextlib import contextmanager
from collections.abc import Iterator
from typing import Any
from datetime import datetime

import numpy as np
import oirfile

from .base_file_loader import BaseFileLoader, ImageHeader, ReferenceImage
from acqstore.utils.logging import get_logger

logger = get_logger(__name__)

def _reference_snapshot_from_oir_reference(ref: Any) -> ReferenceImage:
    """Build a :class:`ReferenceImage` while ``oirfile.OirFile`` is still open."""
    raw = np.asarray(ref.asarray())
    raw.setflags(write=False)
    dims = tuple(str(d) for d in ref.dims)
    sizes: dict[str, int] = dict(ref.sizes)
    num_channels = int(sizes["C"]) if "C" in sizes else 1
    line_roi = ref.line_roi
    if line_roi is not None:
        line_roi = tuple(float(x) for x in line_roi)
    units_t = tuple(sorted((str(k), str(v)) for k, v in ref.coord_units.items()))
    scales_raw = ref.coord_scales
    scales_t = tuple(sorted((str(k), float(v)) for k, v in scales_raw.items()))
    coord_items: list[tuple[str, np.ndarray]] = []
    for key in sorted(ref.coords.keys(), key=str):
        c = np.asarray(ref.coords[key])
        c.setflags(write=False)
        coord_items.append((str(key), c))
    return ReferenceImage(
        array=raw,
        dims=dims,
        num_channels=num_channels,
        line_roi=line_roi,
        coord_units=units_t,
        coord_scales=scales_t,
        coords=tuple(coord_items),
    )

def _step_from_coord(coord: Any) -> float | None:
    """Spacing between the first two samples of a 1D coordinate array.

    Args:
        coord: One-dimensional coordinate array-like, or ``None``.

    Returns:
        Difference as ``float``, or ``None`` if fewer than two points.
    """
    if coord is None or len(coord) < 2:
        return None

    value = coord[1] - coord[0]
    if hasattr(value, "item"):
        value = value.item()
    return float(value)

def _iso8601_datetime_str_to_yyyymmdd_hhmmss(s: str) -> tuple[str, str]:
    """Parse oirfile-style ISO 8601 string; return ``(YYYYMMDD, HH:MM:SS)`` or empty strings."""
    t = s.strip()
    if not t:
        return ("", "")
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(t)
    except ValueError:
        return ("", "")
    return (dt.strftime("%Y%m%d"), dt.strftime("%H:%M:%S"))

def _physical_units_for_header(scene: Any) -> tuple[tuple[Any, ...], tuple[str, ...]]:
    oir = scene
    coords = oir.coords
    n = len(coords)
    physical_units: list[Any] = [None] * n
    physical_units_labels = [""] * n
    for idx, coord_str in enumerate(coords):
        physical_units[idx] = _step_from_coord(coords[coord_str])
        physical_units_labels[idx] = coord_str
    return tuple(physical_units), tuple(physical_units_labels)

def _image_header_from_scene(
    path: str,
    scene: Any,
    num_scenes: int,
) -> ImageHeader:
    """Build an :class:`ImageHeader` from a czifile/oirfile scene-like object.

    Args:
        path: Absolute or resolved path stored on the header.
        scene: Object with ``shape``, ``dims``, ``sizes``, and ``dtype``.
        num_scenes: Total scene count for the file (OIR uses ``1``).

    Returns:
        Frozen :class:`ImageHeader` instance.
    """
    shape = tuple(int(v) for v in scene.shape)
    dims = tuple(str(d) for d in scene.dims)
    sizes = {str(k): int(v) for k, v in scene.sizes.items()}
    dtype = np.dtype(scene.dtype)
    num_channels = int(sizes["C"]) if "C" in sizes else 1
    physical_units, physical_units_labels = _physical_units_for_header(scene)
    date_s, time_s = _date_time_for_header(scene)
    return ImageHeader(
        path=path,
        shape=shape,
        dims=dims,
        sizes=sizes,
        dtype=dtype,
        num_channels=num_channels,
        num_scenes=num_scenes,
        physical_units=physical_units,
        physical_units_labels=physical_units_labels,
        date=date_s,
        time=time_s,
    )

def _date_time_for_header(scene: Any) -> tuple[str, str]:
    oir = scene
    raw = getattr(oir, "datetime", None)
    if raw is None:
        return ("", "")
    return _iso8601_datetime_str_to_yyyymmdd_hhmmss(str(raw))

class OirFileLoader(BaseFileLoader):
    """Lazy-loading OIR reader aligned with :class:`MyCziImage`.

    Pixel data loads on demand. Supported OIR layouts follow the same CYX
    constraints as the helper functions in this module.
    """

    def __init__(self, path: str, header: ImageHeader | None = None) -> None:
        super().__init__(path, header)

    @contextmanager
    def _open_oir(self) -> Iterator[Any]:
        """Yield an ``oirfile.OirFile`` opened from :attr:`path` or :attr:`_stream`."""
        if self._stream is not None:
            self._stream.seek(0)
            with oirfile.OirFile(self._stream) as oir:
                yield oir
        else:
            with oirfile.OirFile(self.path) as oir:
                yield oir

    def reference_image(self) -> ReferenceImage | None:
        """Return a frozen snapshot of the Olympus linescan reference image, if any.

        The snapshot is built while the OIR file is open and is safe to keep after close.

        Returns:
            :class:`ReferenceImageSnapshot`, or ``None`` when the file has no reference.
        """
        if self._referenceImage:
            return self._referenceImage

        with self._open_oir() as oir:
            ref = oir.reference
            if ref is None:
                self._referenceImage = None
            else:
                self._referenceImage = _reference_snapshot_from_oir_reference(ref)

        return self._referenceImage

    def read_header(self) -> ImageHeader:
        return self._read_oir_header()

    def _read_oir_header(self) -> ImageHeader:
        logical = self.path
        with self._open_oir() as oir_file:
            return _image_header_from_scene(logical, oir_file, num_scenes=1)

    def _load_full_image_array(self) -> np.ndarray:
        logger.info('')
        with self._open_oir() as oir:
            return np.asarray(oir.asarray())
