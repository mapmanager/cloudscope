"""Minimal OME-Zarr/NGFF IO helpers for :class:`AcqPixels`.

This module writes a conservative OME-Zarr v0.4-style, Zarr v2-compatible
single-image store. It intentionally keeps acqstore-specific metadata out of the
standard image metadata; higher-level objects write that under ``/acqstore``.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from .acq_pixels import AcqPixels
from .file_loaders.base_file_loader import ImageHeader

_OME_NGFF_VERSION = "0.4"
_DATASET_PATH = "0"


def _import_zarr() -> Any:
    try:
        import zarr
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise ImportError(
            "OME-Zarr IO requires the optional dependency 'zarr'. "
            "Install with: uv add zarr ome-zarr ngff-zarr 'dask[array]'"
        ) from exc
    return zarr


def _open_group(path: str | Path, *, mode: str) -> Any:
    zarr = _import_zarr()
    try:
        return zarr.open_group(str(path), mode=mode, zarr_format=2)
    except TypeError:
        return zarr.open_group(str(path), mode=mode)


def _create_dataset(group: Any, name: str, data: Any) -> Any:
    """Create one Zarr array across Zarr 2 and Zarr 3 Python APIs."""
    arr = np.asarray(data)
    chunks = _default_chunks(arr.shape)

    create_dataset = getattr(group, "create_dataset", None)
    if callable(create_dataset):
        try:
            return create_dataset(name, data=arr, chunks=chunks, overwrite=True)
        except TypeError:
            return create_dataset(
                name,
                shape=arr.shape,
                dtype=arr.dtype,
                chunks=chunks,
                overwrite=True,
                data=arr,
            )

    create_array = getattr(group, "create_array", None)
    if callable(create_array):
        try:
            return create_array(name, data=arr, chunks=chunks, overwrite=True)
        except TypeError:
            return create_array(
                name,
                shape=arr.shape,
                dtype=arr.dtype,
                chunks=chunks,
                overwrite=True,
                data=arr,
            )

    raise TypeError(
        f"Unsupported Zarr group object {type(group)!r}; expected create_dataset() "
        "or create_array()."
    )


def _default_chunks(shape: tuple[int, ...]) -> tuple[int, ...]:
    if not shape:
        return ()
    chunks: list[int] = []
    for axis, size in enumerate(shape):
        # Keep non-spatial axes small and spatial axes moderately chunky.
        if axis >= len(shape) - 2:
            chunks.append(min(int(size), 1024))
        else:
            chunks.append(1)
    return tuple(max(1, x) for x in chunks)


def _axis_type(axis: str) -> str:
    if axis in {"X", "Y", "Z"}:
        return "space"
    if axis == "T":
        return "time"
    if axis == "C":
        return "channel"
    return "space"


def _axis_unit(axis: str, header: ImageHeader) -> str | None:
    if axis not in header.dims:
        return None
    i = header.dims.index(axis)
    if i >= len(header.physical_units_labels):
        return None
    raw = str(header.physical_units_labels[i])
    if not raw or raw.lower() == "pixels":
        return None
    return raw


def _scale_vector(header: ImageHeader) -> list[float]:
    scale: list[float] = []
    for i, _axis in enumerate(header.dims):
        try:
            scale.append(float(header.physical_units[i]))
        except (IndexError, TypeError, ValueError):
            scale.append(1.0)
    return scale


def build_ome_ngff_metadata(pixels: AcqPixels) -> dict[str, Any]:
    """Return OME-NGFF multiscales metadata for one full-resolution dataset."""
    axes = []
    for axis in pixels.axes:
        entry: dict[str, Any] = {"name": axis.lower(), "type": _axis_type(axis)}
        unit = _axis_unit(axis, pixels.header)
        if unit is not None:
            entry["unit"] = unit
        axes.append(entry)
    return {
        "version": _OME_NGFF_VERSION,
        "axes": axes,
        "datasets": [
            {
                "path": _DATASET_PATH,
                "coordinateTransformations": [
                    {"type": "scale", "scale": _scale_vector(pixels.header)}
                ],
            }
        ],
        "metadata": {
            "method": "acqstore",
        },
    }


def write_acq_pixels_ome_zarr(
    pixels: AcqPixels,
    path: str | Path,
    *,
    overwrite: bool = False,
) -> None:
    """Write one acquisition's pixels as an OME-Zarr-compatible store."""
    zarr_path = Path(path)
    if zarr_path.exists():
        if not overwrite:
            raise FileExistsError(f"Zarr store already exists: {zarr_path}")
        if zarr_path.is_dir():
            shutil.rmtree(zarr_path)
        else:
            zarr_path.unlink()
    group = _open_group(zarr_path, mode="w")
    _create_dataset(group, _DATASET_PATH, pixels.get_array(0))
    group.attrs["multiscales"] = [build_ome_ngff_metadata(pixels)]
    group.attrs["omero"] = _build_omero_metadata(pixels)
    group.attrs["acqstore_pixels"] = pixels.as_acqstore_metadata()


def _build_omero_metadata(pixels: AcqPixels) -> dict[str, Any]:
    channels = []
    for c in pixels.channel_indices:
        channels.append(
            {
                "label": f"Channel {c}",
                "active": True,
                "coefficient": 1,
                "color": "FFFFFF",
                "window": {"start": 0, "end": 255, "min": 0, "max": 255},
            }
        )
    return {"channels": channels}


def read_acq_pixels_ome_zarr(path: str | Path, *, lazy: bool = True) -> AcqPixels:
    """Read one OME-Zarr-compatible image store into :class:`AcqPixels`."""
    group = _open_group(path, mode="r")
    attrs = dict(group.attrs)
    dataset_path = _dataset_path_from_attrs(attrs)
    arr = group[dataset_path]
    data: Any = arr if lazy else np.asarray(arr)
    header = _header_from_attrs(path, attrs, arr)
    return AcqPixels(
        data=data,
        header=header,
        source_path=str(Path(path).resolve(strict=False)),
        acquisition_metadata={"ome_ngff": attrs.get("multiscales", [])},
        source_metadata={"zarr_attrs": attrs},
    )


def _dataset_path_from_attrs(attrs: dict[str, Any]) -> str:
    multiscales = attrs.get("multiscales")
    if isinstance(multiscales, list) and multiscales:
        first = multiscales[0]
        if isinstance(first, dict):
            datasets = first.get("datasets")
            if isinstance(datasets, list) and datasets:
                ds = datasets[0]
                if isinstance(ds, dict) and isinstance(ds.get("path"), str):
                    return str(ds["path"])
    return _DATASET_PATH


def _header_from_attrs(path: str | Path, attrs: dict[str, Any], arr: Any) -> ImageHeader:
    acqstore_pixels = attrs.get("acqstore_pixels")
    if isinstance(acqstore_pixels, dict):
        raw_header = acqstore_pixels.get("header")
        if isinstance(raw_header, dict):
            return _header_from_json_dict(path, raw_header)

    dims = _dims_from_multiscales(attrs, int(arr.ndim))
    shape = tuple(int(x) for x in arr.shape)
    sizes = {dims[i]: shape[i] for i in range(len(dims))}
    dtype = np.dtype(arr.dtype)
    num_channels = int(sizes.get("C", 1))
    physical_units, physical_units_labels = _physical_from_multiscales(attrs, dims)
    return ImageHeader(
        path=str(Path(path).resolve(strict=False)),
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
    ).with_coerced_physical_calibration()


def _header_from_json_dict(path: str | Path, raw: dict[str, Any]) -> ImageHeader:
    dims = tuple(str(x).upper() for x in raw.get("dims", ()))
    shape = tuple(int(x) for x in raw.get("shape", ()))
    sizes = {str(k).upper(): int(v) for k, v in dict(raw.get("sizes", {})).items()}
    if not dims:
        dims = _default_dims_for_ndim(len(shape))
    if not sizes:
        sizes = {dims[i]: shape[i] for i in range(len(dims))}
    physical_units = tuple(1.0 if x is None else x for x in raw.get("physical_units", ()))
    physical_units_labels = tuple(str(x) for x in raw.get("physical_units_labels", ()))
    return ImageHeader(
        path=str(Path(path).resolve(strict=False)),
        shape=shape,
        dims=dims,
        sizes=sizes,
        dtype=np.dtype(str(raw.get("dtype", "uint8"))),
        num_channels=int(raw.get("num_channels", sizes.get("C", 1))),
        num_scenes=1,
        physical_units=physical_units,
        physical_units_labels=physical_units_labels,
        date=str(raw.get("date", "")),
        time=str(raw.get("time", "")),
    ).with_coerced_physical_calibration()


def _dims_from_multiscales(attrs: dict[str, Any], ndim: int) -> tuple[str, ...]:
    multiscales = attrs.get("multiscales")
    if isinstance(multiscales, list) and multiscales and isinstance(multiscales[0], dict):
        axes = multiscales[0].get("axes")
        if isinstance(axes, list) and len(axes) == ndim:
            names: list[str] = []
            for axis in axes:
                if isinstance(axis, dict) and isinstance(axis.get("name"), str):
                    names.append(str(axis["name"]).upper())
            if len(names) == ndim:
                return tuple(names)
    return _default_dims_for_ndim(ndim)


def _default_dims_for_ndim(ndim: int) -> tuple[str, ...]:
    if ndim == 2:
        return ("Y", "X")
    if ndim == 3:
        return ("Z", "Y", "X")
    if ndim == 4:
        return ("C", "Z", "Y", "X")
    if ndim == 5:
        return ("T", "C", "Z", "Y", "X")
    raise ValueError(f"Unsupported OME-Zarr array rank {ndim}; expected 2-5")


def _physical_from_multiscales(
    attrs: dict[str, Any],
    dims: tuple[str, ...],
) -> tuple[tuple[float, ...], tuple[str, ...]]:
    units = [1.0 for _ in dims]
    labels = ["Pixels" for _ in dims]
    multiscales = attrs.get("multiscales")
    if isinstance(multiscales, list) and multiscales and isinstance(multiscales[0], dict):
        axes = multiscales[0].get("axes")
        if isinstance(axes, list):
            for i, axis in enumerate(axes[: len(dims)]):
                if isinstance(axis, dict) and axis.get("unit"):
                    labels[i] = str(axis["unit"])
        datasets = multiscales[0].get("datasets")
        if isinstance(datasets, list) and datasets and isinstance(datasets[0], dict):
            txs = datasets[0].get("coordinateTransformations")
            if isinstance(txs, list):
                for tx in txs:
                    if isinstance(tx, dict) and tx.get("type") == "scale":
                        scale = tx.get("scale")
                        if isinstance(scale, list) and len(scale) == len(dims):
                            for i, value in enumerate(scale):
                                try:
                                    units[i] = float(value)
                                except (TypeError, ValueError):
                                    units[i] = 1.0
                            break
    return tuple(units), tuple(labels)


def write_json_file(path: str | Path, payload: dict[str, Any]) -> None:
    """Write an indented JSON file, creating parent directories."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def read_json_file(path: str | Path) -> dict[str, Any]:
    """Read a JSON object from disk."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return raw
