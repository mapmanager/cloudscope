"""Tests for lazy TIFF loading through :class:`TiffFileLoader`."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
import tifffile

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.file_loaders.tiff_file_loader import TiffFileLoader


def _write_synthetic_tif(
    path: Path,
    shape: tuple[int, ...] = (12, 8),
    *,
    dtype: np.dtype | type[np.generic] = np.uint16,
    axes: str | None = None,
) -> np.ndarray:
    """Write a small deterministic TIFF and return the source array."""
    arr = np.arange(int(np.prod(shape)), dtype=dtype).reshape(shape)
    metadata = {"axes": axes} if axes is not None else None
    tifffile.imwrite(path, arr, metadata=metadata, photometric="minisblack")
    return arr


def test_tiff_loader_header_does_not_load_pixels(tmp_path: Path) -> None:
    """Constructing a TIFF loader should read metadata without caching pixels."""
    path = tmp_path / "lazy_header.tif"
    _write_synthetic_tif(path, shape=(30, 18), axes="YX")

    loader = TiffFileLoader(str(path), load_olympus_header=False)

    assert loader.pixels_loaded() is False
    assert loader.header.shape == (30, 18)
    assert loader.header.dims == ("Y", "X")
    assert loader.header.sizes == {"Y": 30, "X": 18}
    assert loader.header.dtype == np.dtype(np.uint16)
    assert loader.header.num_channels == 1
    assert loader.header.num_scenes == 1


def test_tiff_loader_lazy_loads_pixels_on_load_image_data(tmp_path: Path) -> None:
    """TIFF pixels should materialize only through load_image_data."""
    path = tmp_path / "load_pixels_later.tif"
    expected = _write_synthetic_tif(path, shape=(10, 6), axes="YX")
    loader = TiffFileLoader(str(path), load_olympus_header=False)

    assert loader.pixels_loaded() is False
    actual = loader.load_image_data()

    assert loader.pixels_loaded() is True
    np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize(
    ("axes", "shape", "expected_dims", "expected_channels"),
    [
        ("YX", (20, 10), ("Y", "X"), 1),
        ("CYX", (2, 20, 10), ("C", "Y", "X"), 2),
        ("TZYX", (3, 4, 20, 10), ("T", "Z", "Y", "X"), 1),
        ("TCZYX", (2, 3, 4, 20, 10), ("T", "C", "Z", "Y", "X"), 3),
    ],
)
def test_tiff_loader_header_from_tifffile_series_axes(
    tmp_path: Path,
    axes: str,
    shape: tuple[int, ...],
    expected_dims: tuple[str, ...],
    expected_channels: int,
) -> None:
    """Synthetic TIFF axis metadata should round-trip into ImageHeader dims."""
    path = tmp_path / f"axes_{axes}.tif"
    _write_synthetic_tif(path, shape=shape, axes=axes)

    loader = TiffFileLoader(str(path), load_olympus_header=False)

    assert loader.pixels_loaded() is False
    assert loader.header.shape == shape
    assert loader.header.dims == expected_dims
    assert loader.header.sizes == {
        expected_dims[index]: int(shape[index]) for index in range(len(shape))
    }
    assert loader.header.num_channels == expected_channels


def test_tiff_loader_from_stream_header_does_not_load_pixels(tmp_path: Path) -> None:
    """Stream-backed TIFF loaders should also initialize from metadata only."""
    path = tmp_path / "stream_source.tif"
    expected = _write_synthetic_tif(path, shape=(7, 5), axes="YX")
    stream = BytesIO(path.read_bytes())

    loader = TiffFileLoader.from_stream(stream, "stream_source.tif")

    assert loader.pixels_loaded() is False
    assert loader.header.path == "stream_source.tif"
    assert loader.header.shape == (7, 5)
    actual = loader.load_image_data()
    np.testing.assert_array_equal(actual, expected)


def test_acq_image_tif_load_images_false_stays_unloaded(tmp_path: Path) -> None:
    """AcqImage should keep TIFF pixels unloaded when load_images is false."""
    path = tmp_path / "acq_image_lazy.tif"
    expected = _write_synthetic_tif(path, shape=(9, 4), axes="YX")

    acq = AcqImage(str(path), load_images=False, load_analysis_csv=False)

    assert acq.images_loaded is False
    assert acq.pixels_loaded() is False
    assert acq.images.header.shape == (9, 4)
    acq.load_images()
    assert acq.images_loaded is True
    np.testing.assert_array_equal(acq.pixels.data, expected)
