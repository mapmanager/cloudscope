"""Focused tests for acqstore OME-Zarr helper functions."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

zarr = pytest.importorskip("zarr")
bioio_ome_zarr = pytest.importorskip("bioio_ome_zarr")

from acqstore.acq_image.acq_pixels import AcqPixels
from acqstore.acq_image.file_loaders.base_file_loader import ImageHeader
from acqstore.acq_image.ome_zarr_io import (
    _default_dims_for_ndim,
    _dataset_path_from_attrs,
    build_ome_ngff_metadata,
    read_acq_pixels_ome_zarr,
    read_json_file,
    write_acq_pixels_ome_zarr,
    write_json_file,
)


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


def test_build_ome_ngff_metadata_includes_axis_units() -> None:
    """OME-NGFF metadata should preserve spatial axis units from the header."""
    meta = build_ome_ngff_metadata(_pixels(Path("sample.cs.ome.zarr")))

    assert meta["version"] == "0.5"
    assert [axis["name"] for axis in meta["axes"]] == ["z", "y", "x"]
    assert meta["axes"][1]["unit"] == "micrometer"


def test_dataset_path_from_attrs_uses_multiscales_path() -> None:
    """Reader should honor multiscales dataset path when present."""
    attrs = {"multiscales": [{"datasets": [{"path": "data"}]}]}

    assert _dataset_path_from_attrs(attrs) == "data"


def test_dataset_path_from_attrs_falls_back_to_zero() -> None:
    """Missing multiscales metadata should fall back to dataset '0'."""
    assert _dataset_path_from_attrs({}) == "0"


def test_default_dims_for_ndim_maps_supported_ranks() -> None:
    """Unsupported ranks should fail fast."""
    assert _default_dims_for_ndim(2) == ("Y", "X")
    assert _default_dims_for_ndim(3) == ("Z", "Y", "X")
    with pytest.raises(ValueError, match="Unsupported OME-Zarr array rank"):
        _default_dims_for_ndim(1)


def test_read_acq_pixels_ome_zarr_lazy_does_not_materialize_array(tmp_path: Path) -> None:
    """Lazy reads should keep a zarr-backed array until materialization is requested."""
    path = tmp_path / "sample.cs.ome.zarr"
    write_acq_pixels_ome_zarr(_pixels(path), path)

    loaded = read_acq_pixels_ome_zarr(path, lazy=True)

    assert hasattr(loaded.get_array(0), "shape")
    np.testing.assert_array_equal(loaded.get_array(), _pixels(path).get_array())


def test_write_acq_pixels_ome_zarr_refuses_existing_store_without_overwrite(tmp_path: Path) -> None:
    """Writer should fail fast when the destination already exists."""
    path = tmp_path / "sample.cs.ome.zarr"
    write_acq_pixels_ome_zarr(_pixels(path), path)

    with pytest.raises(FileExistsError, match="already exists"):
        write_acq_pixels_ome_zarr(_pixels(path), path, overwrite=False)


def test_json_file_helpers_round_trip_object(tmp_path: Path) -> None:
    """JSON helpers should read and write one top-level object."""
    target = tmp_path / "nested" / "meta.json"
    payload = {"schema_version": 1, "values": [1, 2, 3]}

    write_json_file(target, payload)

    assert read_json_file(target) == payload


def test_read_json_file_rejects_non_object(tmp_path: Path) -> None:
    """JSON arrays at the root should be rejected."""
    target = tmp_path / "bad.json"
    target.write_text("[1, 2, 3]", encoding="utf-8")

    with pytest.raises(ValueError, match="Expected JSON object"):
        read_json_file(target)
