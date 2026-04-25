from __future__ import annotations  # treat all type hints as strings

from contextlib import contextmanager
from collections.abc import Iterator
from typing import BinaryIO
import numpy as np
import tifffile
from typing import Self

from .base_file_loader import BaseFileLoader, ImageHeader
from .read_olympus_txt import read_olympus_txt_dict, _image_header_from_olympus_dict
from cloudscope.core.utils.logging import get_logger

logger = get_logger(__name__)


class TiffFileLoader(BaseFileLoader):
    """TIFF reader using ``tifffile.imread``; header from pixels and/or Olympus sidecar ``.txt``.

    Axis labels: 2D ``(Y,X)``, 3D ``(Z,Y,X)``, 4D ``(C,Z,Y,X)``. ``ndim > 4`` raises.
    If ``load_olympus_header`` is true and a companion Olympus ``.txt`` exists, the
    header can be built **without** reading pixels (lazy); loading pixels then
    validates array shape against that header (fail fast on mismatch).

    Args:
        path: Filesystem path to the TIFF.
        header: Optional pre-built header (e.g. from catalog Olympus parse).
        load_olympus_header: When true (default), look for Olympus ``.txt`` next to
            the TIFF on disk. Ignored when ``header`` is provided. Use false for
            streams or to force metadata-only-from-pixeldata behavior.
    """

    def __init__(
        self,
        path: str,
        header: ImageHeader | None = None,
        *,
        load_olympus_header: bool = True,
    ) -> None:
        self._load_olympus_header = load_olympus_header
        super().__init__(path, header)

    @contextmanager
    def _open_tif(self) -> Iterator[BinaryIO | str]:
        """Yield :attr:`path` or rewound :attr:`_stream` for :func:`tifffile.imread`."""
        if self._stream is not None:
            self._stream.seek(0)
            yield self._stream
        else:
            yield self.path

    @classmethod
    def from_stream(
        cls,
        stream: BinaryIO,
        filename: str,
        header: ImageHeader | None = None,
        *,
        load_olympus_header: bool = False,
    ) -> Self:
        inst = super().from_stream(stream, filename, header)
        inst._load_olympus_header = load_olympus_header  # Add the TIFF-specific attribute
        return inst

    def read_header(self) -> ImageHeader:
        return self._read_tif_header()

    def _read_tif_array(self) -> np.ndarray:
        with self._open_tif() as src:
            return np.asarray(tifffile.imread(src))

    def _read_tif_header(self) -> ImageHeader:
        if self._stream is None and self._load_olympus_header:
            odict = read_olympus_txt_dict(self.path)
            if odict is not None:
                try:
                    return _image_header_from_olympus_dict(self.path, odict)
                except (ValueError, TypeError, KeyError) as exc:
                    logger.warning(
                        f'Olympus txt present but ImageHeader build failed, falling back to pixel read: {exc}',
                    )
        # did not get tif header -> expensive load all data to make header
        arr = self._read_tif_array()
        ndim = arr.ndim
        dims = ImageHeader.dims_from_ndim(ndim)
        shape = tuple(int(x) for x in arr.shape)
        sizes = {dims[i]: shape[i] for i in range(ndim)}
        dtype = np.dtype(arr.dtype)
        num_channels = int(sizes["C"]) if "C" in sizes else 1
        physical_units, physical_units_labels = ImageHeader.default_physical_for_dims(dims)
        self._img_data = arr
        return ImageHeader(
            path=self.path,
            shape=shape,
            dims=dims,
            sizes=sizes,
            dtype=dtype,
            num_channels=num_channels,
            num_scenes=1,
            physical_units=physical_units,
            physical_units_labels=physical_units_labels,
            date="",
            time="",
        )

    def _load_full_image_array(self) -> np.ndarray:
        if self._img_data is not None:
            return self._img_data
        arr = self._read_tif_array()
        hdr = self._header
        if hdr is not None:
            expected = tuple(int(x) for x in hdr.shape)
            got = tuple(int(x) for x in arr.shape)
            if expected != got:
                raise ValueError(
                    f"TIFF array shape {got} does not match header shape {expected}"
                )
        return arr
