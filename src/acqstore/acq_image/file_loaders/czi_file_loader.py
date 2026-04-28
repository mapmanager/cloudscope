from contextlib import contextmanager
from collections.abc import Iterator
from typing import Any
from typing import BinaryIO

import numpy as np
import czifile

from .base_file_loader import BaseFileLoader, ImageHeader
from .oir_file_loader import _image_header_from_scene
from acqstore.utils.logging import get_logger

logger = get_logger(__name__)

class CziFileLoader(BaseFileLoader):
    """Lazy-loading CZI reader for scene ``0`` only."""

    def __init__(self, path: str, header: ImageHeader | None = None) -> None:
        super().__init__(path, header)

    @contextmanager
    def _open_czi(self) -> Iterator[Any]:
        """Yield an ``czifile.CziFile`` opened from :attr:`path` or :attr:`_stream`."""
        if self._stream is not None:
            self._stream.seek(0)
            with czifile.CziFile(self._stream) as czi:
                yield czi
        else:
            with czifile.CziFile(self.path) as czi:
                yield czi

    @classmethod
    def read_header_from_stream(cls, stream: BinaryIO, filename: str) -> ImageHeader:
        """Read CZI header from a stream without retaining the loader."""
        return cls.from_stream(stream, filename).header

    def read_header(self) -> ImageHeader:
        return self._read_czi_header()

    def _physical_units_for_header(self, scene: Any) -> tuple[tuple[Any, ...], tuple[str, ...]]:
        czi_scene = scene
        xarr = czi_scene.asxarray()
        n = len(xarr.coords)
        _physical_units: list[Any] = [None] * n
        _physical_units_labels = [""] * n
        for idx, coord_str in enumerate(xarr.coords):
            if xarr[coord_str] is None or len(xarr[coord_str]) < 2:
                _physical_units[idx] = None
                _physical_units_labels[idx] = "unknown"
                continue
            value0 = xarr[coord_str][1] - xarr[coord_str][0]
            value: Any = value0.item()
            if coord_str in ("X", "Y"):
                value = float(value) * 1e6
            elif coord_str == "C":
                value = float("nan")
            _physical_units[idx] = value
            if coord_str in ("X", "Y"):
                _physical_units_labels[idx] = "um"
            elif coord_str == "T":
                _physical_units_labels[idx] = "seconds"
            else:
                _physical_units_labels[idx] = "unknown"

        return tuple(_physical_units), tuple(_physical_units_labels)

    def _read_czi_header(self) -> ImageHeader:
        """Read header information from the first scene of a CZI file.

        Common dimension patterns include ``('C','T','X')`` (line-scan),
        ``('C','T','Y','X')`` (frames), and ``('C','Y','X')`` (2D).
        """
        logical = self.path
        with self._open_czi() as czi_file:
            num_scenes = len(czi_file.scenes)
            scene = czi_file.scenes[0]
            return _image_header_from_scene(logical, scene, num_scenes=num_scenes)

    def _load_full_image_array(self) -> np.ndarray:
        logger.info('')
        with self._open_czi() as czi_file:
            return np.asarray(czi_file.scenes[0].asarray())
