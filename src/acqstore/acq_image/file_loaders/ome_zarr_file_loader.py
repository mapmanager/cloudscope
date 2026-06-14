"""OME-Zarr/NGFF file loader."""

from __future__ import annotations

import numpy as np

from ..acq_pixels import AcqPixels
from ..ome_zarr_io import read_acq_pixels_ome_zarr
from .base_file_loader import BaseFileLoader, ImageHeader


class OmeZarrFileLoader(BaseFileLoader):
    """Loader for single-image ``.ome.zarr`` and ``.cs.ome.zarr`` stores."""

    def _post_init(self, header: ImageHeader | None) -> None:
        self._pixels: AcqPixels | None = None
        super()._post_init(header)

    def read_header(self) -> ImageHeader:
        pixels = self._load_pixels_lazy()
        return pixels.header

    def _load_pixels_lazy(self) -> AcqPixels:
        if self._pixels is None:
            self._pixels = read_acq_pixels_ome_zarr(self.path, lazy=True)
        return self._pixels

    def load_pixels(self) -> AcqPixels:
        """Return Zarr-backed pixels without eagerly loading the full array."""
        return self._load_pixels_lazy()

    def _load_full_image_array(self) -> np.ndarray:
        return np.asarray(self._load_pixels_lazy().get_array(0))
