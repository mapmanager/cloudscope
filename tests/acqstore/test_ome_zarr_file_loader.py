"""Tests for acqstore native OME-Zarr single-acquisition IO."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

zarr = pytest.importorskip("zarr")

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.acq_pixels import AcqPixels
from acqstore.acq_image.file_loaders.base_file_loader import ImageHeader
from acqstore.acq_image.file_loaders.file_loader_factory import create_file_loader
from acqstore.acq_image.file_loaders.ome_zarr_file_loader import OmeZarrFileLoader
from acqstore.acq_image.ome_zarr_io import read_acq_pixels_ome_zarr, write_acq_pixels_ome_zarr


def _pixels(path: Path) -> AcqPixels:
    data = np.arange(2 * 3 * 4, dtype=np.uint16).reshape(2, 3, 4)
    dims = ("Z", "Y", "X")
    return AcqPixels(
        data=data,
        header=ImageHeader(
            path=str(path),
            shape=data.shape,
            dims=dims,
            sizes={dims[i]: int(data.shape[i]) for i in range(len(dims))},
            dtype=data.dtype,
            num_channels=1,
            num_scenes=1,
            physical_units=(1.0, 0.5, 0.25),
            physical_units_labels=("Pixels", "micrometer", "micrometer"),
            date="20260102",
            time="03:04:05",
        ),
        source_path=str(path),
    )


def test_write_and_read_acq_pixels_ome_zarr_round_trips_header_and_data(tmp_path: Path) -> None:
    path = tmp_path / "sample.cs.ome.zarr"
    pixels = _pixels(path)

    write_acq_pixels_ome_zarr(pixels, path)
    loaded = read_acq_pixels_ome_zarr(path, lazy=False)

    assert loaded.axes == ("Z", "Y", "X")
    assert loaded.shape == (2, 3, 4)
    assert loaded.header.physical_units == (1.0, 0.5, 0.25)
    np.testing.assert_array_equal(loaded.get_array(), pixels.get_array())


def test_create_file_loader_returns_ome_zarr_loader_for_compound_suffix(tmp_path: Path) -> None:
    path = tmp_path / "sample.cs.ome.zarr"
    write_acq_pixels_ome_zarr(_pixels(path), path)

    loader = create_file_loader(str(path))

    assert isinstance(loader, OmeZarrFileLoader)
    assert loader.header.dims == ("Z", "Y", "X")


def test_acq_image_save_native_zarr_embeds_acqstore_sidecar(tmp_path: Path) -> None:
    import tifffile

    src = tmp_path / "source.tif"
    tifffile.imwrite(src, np.arange(12, dtype=np.uint16).reshape(3, 4))
    acq = AcqImage(str(src))
    acq.apply_metadata_patch("experiment_metadata", {"species": "mouse"})

    dest = tmp_path / "source.cs.ome.zarr"
    acq.save_native_zarr(dest)

    reloaded = AcqImage(str(dest))
    assert reloaded.pixels.axes == ("Y", "X")
    assert reloaded.get_metadata_section("experiment_metadata").get_values()["species"] == "mouse"
    np.testing.assert_array_equal(reloaded.pixels.get_plane(), np.arange(12, dtype=np.uint16).reshape(3, 4))
