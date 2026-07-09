"""Tests for AcqImage TIFF export helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import tifffile

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.tiff_export import save_pixels_as_tif
from acqstore.acq_image.acq_pixels import AcqPixels
from acqstore.acq_image.file_loaders.base_file_loader import ImageHeader


def _pixels(path: Path) -> AcqPixels:
    data = np.arange(3 * 4, dtype=np.uint16).reshape(3, 4)
    header = ImageHeader(
        path=str(path),
        shape=data.shape,
        dims=('Y', 'X'),
        sizes={'Y': 3, 'X': 4},
        dtype=data.dtype,
        num_channels=1,
        num_scenes=1,
        physical_units=(0.5, 0.25),
        physical_units_labels=('micrometer', 'micrometer'),
    )
    return AcqPixels(data=data, header=header, source_path=str(path))


def test_save_pixels_as_tif_writes_full_data(tmp_path: Path) -> None:
    """TIFF export should write the full array, not a display plane subset."""
    dest = tmp_path / 'export.tif'
    pixels = _pixels(dest)

    save_pixels_as_tif(pixels, dest)

    np.testing.assert_array_equal(tifffile.imread(dest), pixels.get_array())


def test_save_pixels_as_tif_refuses_existing_file_without_overwrite(tmp_path: Path) -> None:
    """TIFF export should fail fast rather than silently replacing files."""
    dest = tmp_path / 'export.tif'
    pixels = _pixels(dest)
    save_pixels_as_tif(pixels, dest)

    with pytest.raises(FileExistsError, match='already exists'):
        save_pixels_as_tif(pixels, dest)


def test_acq_image_save_as_tif_requires_explicit_filename(tmp_path: Path) -> None:
    """AcqImage TIFF export should use exactly the caller-provided filename."""
    src = tmp_path / 'source.tif'
    data = np.arange(12, dtype=np.uint16).reshape(3, 4)
    tifffile.imwrite(src, data)
    acq = AcqImage(str(src))
    dest = tmp_path / 'chosen_name.tif'

    acq.save_as_tif(dest)

    assert dest.is_file()
    np.testing.assert_array_equal(tifffile.imread(dest), data)
