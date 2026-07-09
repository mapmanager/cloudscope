"""OME-Zarr/NGFF IO helpers for :class:`~acqstore.acq_image.acq_pixels.AcqPixels`.

The public acqstore API is intentionally independent of the concrete OME-Zarr
implementation library. Writing uses ``bioio-ome-zarr`` when available so new
exports default to OME-NGFF 0.5 / Zarr v3 while still allowing Zarr v2 on
request. Reading uses Zarr metadata directly so acqstore can hydrate its own
``ImageHeader`` and lazy array wrapper without leaking BioIO objects.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from .acq_pixels import AcqPixels
from .file_loaders.base_file_loader import ImageHeader
from .zarr_store_utils import (
    ensure_store_absent,
    is_s3_path,
    is_zip_store_path,
    read_json_file,
    write_json_file,
    zip_directory_store,
)

_OME_NGFF_VERSION_BY_FORMAT = {2: '0.4', 3: '0.5'}
_DEFAULT_ZARR_FORMAT = 3
_DATASET_PATH = '0'
_MIN_PYRAMID_SPATIAL_SIZE = 16


def _import_zarr() -> Any:
    try:
        import zarr
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise ImportError(
            "OME-Zarr reads require optional dependency 'zarr'. Install with: uv add zarr"
        ) from exc
    return zarr


def _import_bioio_writer() -> type[Any]:
    try:
        from bioio_ome_zarr.writers import OMEZarrWriter
    except ImportError as exc:  # pragma: no cover - depends on optional dependency
        raise ImportError(
            "OME-Zarr exports require optional dependency 'bioio-ome-zarr'. "
            'Install with: uv add bioio bioio-ome-zarr s3fs boto3'
        ) from exc
    return OMEZarrWriter


def _open_group(path: str | Path, *, mode: str) -> Any:
    zarr = _import_zarr()
    path_text = str(path)
    if is_zip_store_path(path_text):
        zip_store_cls = getattr(getattr(zarr, 'storage', object()), 'ZipStore', None)
        if zip_store_cls is None:
            raise ImportError('Reading ZIP-backed Zarr stores requires zarr.storage.ZipStore')
        store = zip_store_cls(path_text, mode='r')
        try:
            return zarr.open_group(store=store, mode=mode)
        except TypeError:
            return zarr.open_group(store, mode=mode)
    try:
        return zarr.open_group(store=path_text, mode=mode)
    except TypeError:
        return zarr.open_group(path_text, mode=mode)


def _axis_type(axis: str) -> str:
    if axis in {'X', 'Y', 'Z'}:
        return 'space'
    if axis == 'T':
        return 'time'
    if axis == 'C':
        return 'channel'
    return 'space'


def _axis_unit(axis: str, header: ImageHeader) -> str | None:
    if axis not in header.dims:
        return None
    i = header.dims.index(axis)
    if i >= len(header.physical_units_labels):
        return None
    raw = str(header.physical_units_labels[i])
    if not raw or raw.lower() == 'pixels':
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


def build_ome_ngff_metadata(
    pixels: AcqPixels,
    *,
    zarr_format: int = _DEFAULT_ZARR_FORMAT,
) -> dict[str, Any]:
    """Return expected OME-NGFF multiscales metadata for ``pixels``.

    Args:
        pixels: Source pixels and acquisition metadata.
        zarr_format: Target Zarr format, ``3`` for NGFF 0.5 or ``2`` for NGFF
            0.4.

    Returns:
        OME-NGFF ``multiscales`` entry for one image.

    Raises:
        ValueError: If ``zarr_format`` is not ``2`` or ``3``.
    """
    version = _ngff_version_for_zarr_format(zarr_format)
    axes = []
    for axis in pixels.axes:
        entry: dict[str, Any] = {'name': axis.lower(), 'type': _axis_type(axis)}
        unit = _axis_unit(axis, pixels.header)
        if unit is not None:
            entry['unit'] = unit
        axes.append(entry)
    datasets = []
    for level, shape in enumerate(build_multiscale_level_shapes(pixels.shape, pixels.axes)):
        scale = _level_scale_vector(pixels.header, pixels.shape, shape)
        datasets.append(
            {
                'path': str(level),
                'coordinateTransformations': [{'type': 'scale', 'scale': scale}],
            }
        )
    return {
        'version': version,
        'axes': axes,
        'datasets': datasets,
        'metadata': {'method': 'acqstore'},
    }


def build_multiscale_level_shapes(
    shape: tuple[int, ...],
    axes: tuple[str, ...],
    *,
    min_spatial_size: int = _MIN_PYRAMID_SPATIAL_SIZE,
) -> list[tuple[int, ...]]:
    """Return pyramid level shapes with Y/X downsampled by powers of two.

    Args:
        shape: Full-resolution shape.
        axes: Axis labels aligned with ``shape``.
        min_spatial_size: Stop once either spatial axis would fall below this
            size.

    Returns:
        Level-0-first list of shapes. Small images may return only level 0.

    Raises:
        ValueError: If ``axes`` does not contain Y and X.
    """
    if 'Y' not in axes or 'X' not in axes:
        raise ValueError(f'OME-Zarr export requires Y and X axes; got {axes!r}')
    levels = [tuple(int(x) for x in shape)]
    y_axis = axes.index('Y')
    x_axis = axes.index('X')
    current = list(levels[0])
    while current[y_axis] // 2 >= min_spatial_size and current[x_axis] // 2 >= min_spatial_size:
        current = list(current)
        current[y_axis] = max(1, current[y_axis] // 2)
        current[x_axis] = max(1, current[x_axis] // 2)
        levels.append(tuple(current))
    return levels


def write_acq_pixels_ome_zarr(
    pixels: AcqPixels,
    path: str | Path,
    *,
    overwrite: bool = False,
    zarr_format: int = _DEFAULT_ZARR_FORMAT,
    include_acqstore_pixels: bool = True,
) -> None:
    """Write one acquisition's pixels as an OME-Zarr-compatible store.

    Args:
        pixels: Pixel object to write.
        path: Destination store. Local directory stores, local ``.zip`` stores,
            and ``s3://`` fsspec paths are supported.
        overwrite: Whether to replace an existing local destination. S3 overwrite
            cleanup must be performed by the caller or AWS CLI.
        zarr_format: Target Zarr format. ``3`` writes NGFF 0.5; ``2`` writes
            NGFF 0.4.
        include_acqstore_pixels: When true, embed a lightweight acqstore header
            snapshot in root attrs for round-tripping.

    Raises:
        ValueError: If ``zarr_format`` is not ``2`` or ``3``.
        ImportError: If ``bioio-ome-zarr`` is missing.
    """
    _ngff_version_for_zarr_format(zarr_format)
    if is_zip_store_path(path):
        if is_s3_path(path):
            raise ValueError('ZIP-backed OME-Zarr writes are only supported for local paths')
        with tempfile.TemporaryDirectory(prefix='acqstore_ome_zarr_') as tmpdir:
            tmp_store = Path(tmpdir) / Path(str(path)[:-4]).name
            _write_acq_pixels_ome_zarr_directory(
                pixels,
                tmp_store,
                overwrite=True,
                zarr_format=zarr_format,
                include_acqstore_pixels=include_acqstore_pixels,
            )
            zip_directory_store(tmp_store, path, overwrite=overwrite)
        return
    _write_acq_pixels_ome_zarr_directory(
        pixels,
        path,
        overwrite=overwrite,
        zarr_format=zarr_format,
        include_acqstore_pixels=include_acqstore_pixels,
    )


def _write_acq_pixels_ome_zarr_directory(
    pixels: AcqPixels,
    path: str | Path,
    *,
    overwrite: bool,
    zarr_format: int,
    include_acqstore_pixels: bool,
) -> None:
    if not is_s3_path(path):
        ensure_store_absent(path, overwrite=overwrite)
    writer_cls = _import_bioio_writer()
    arr = np.asarray(pixels.get_array(0))
    level_shapes = build_multiscale_level_shapes(tuple(int(x) for x in arr.shape), pixels.axes)
    writer = writer_cls(
        store=str(path),
        level_shapes=level_shapes,
        dtype=arr.dtype,
        zarr_format=zarr_format,
        axes_names=[axis.lower() for axis in pixels.axes],
        axes_types=[_axis_type(axis) for axis in pixels.axes],
        axes_units=[_axis_unit(axis, pixels.header) for axis in pixels.axes],
        physical_pixel_size=_scale_vector(pixels.header),
        image_name=Path(str(path).rstrip('/')).name,
        creator_info={'name': 'acqstore', 'version': '0.1'} if zarr_format == 3 else None,
    )
    writer.write_full_volume(arr)
    if include_acqstore_pixels:
        _write_root_acqstore_pixels_attrs(path, pixels)


def _write_root_acqstore_pixels_attrs(path: str | Path, pixels: AcqPixels) -> None:
    group = _open_group(path, mode='a')
    group.attrs['acqstore_pixels'] = pixels.as_acqstore_metadata()


def _ngff_version_for_zarr_format(zarr_format: int) -> str:
    try:
        return _OME_NGFF_VERSION_BY_FORMAT[int(zarr_format)]
    except (KeyError, ValueError) as exc:
        raise ValueError(f'zarr_format must be 2 or 3, got {zarr_format!r}') from exc


def _level_scale_vector(
    header: ImageHeader,
    base_shape: tuple[int, ...],
    level_shape: tuple[int, ...],
) -> list[float]:
    base_scale = _scale_vector(header)
    out: list[float] = []
    for i, scale in enumerate(base_scale):
        if i >= len(base_shape) or i >= len(level_shape):
            out.append(scale)
            continue
        if int(level_shape[i]) <= 0:
            out.append(scale)
            continue
        out.append(float(scale) * (float(base_shape[i]) / float(level_shape[i])))
    return out


def read_acq_pixels_ome_zarr(path: str | Path, *, lazy: bool = True) -> AcqPixels:
    """Read one OME-Zarr-compatible image store into :class:`AcqPixels`.

    Args:
        path: Local, local-ZIP, or S3-backed OME-Zarr store.
        lazy: When true, keep the full-resolution backing array lazy when the
            underlying Zarr implementation supports it.

    Returns:
        Loaded :class:`AcqPixels` wrapper.
    """
    group = _open_group(path, mode='r')
    attrs = dict(group.attrs)
    dataset_path = _dataset_path_from_attrs(attrs)
    arr = group[dataset_path]
    data: Any = arr if lazy else np.asarray(arr)
    levels = _read_pyramid_levels(group, attrs, lazy=lazy)
    header = _header_from_attrs(path, attrs, arr)
    return AcqPixels(
        data=data,
        header=header,
        source_path=str(path),
        acquisition_metadata={'ome_ngff': attrs.get('multiscales', [])},
        source_metadata={'zarr_attrs': attrs},
        levels=levels,
    )


def _read_pyramid_levels(group: Any, attrs: dict[str, Any], *, lazy: bool) -> tuple[Any, ...]:
    multiscales = attrs.get('multiscales')
    if not isinstance(multiscales, list) or not multiscales or not isinstance(multiscales[0], dict):
        return ()
    datasets = multiscales[0].get('datasets')
    if not isinstance(datasets, list) or len(datasets) <= 1:
        return ()
    out: list[Any] = []
    for ds in datasets[1:]:
        if not isinstance(ds, dict) or not isinstance(ds.get('path'), str):
            continue
        arr = group[str(ds['path'])]
        out.append(arr if lazy else np.asarray(arr))
    return tuple(out)


def _dataset_path_from_attrs(attrs: dict[str, Any]) -> str:
    multiscales = attrs.get('multiscales')
    if isinstance(multiscales, list) and multiscales:
        first = multiscales[0]
        if isinstance(first, dict):
            datasets = first.get('datasets')
            if isinstance(datasets, list) and datasets:
                ds = datasets[0]
                if isinstance(ds, dict) and isinstance(ds.get('path'), str):
                    return str(ds['path'])
    return _DATASET_PATH


def _header_from_attrs(path: str | Path, attrs: dict[str, Any], arr: Any) -> ImageHeader:
    acqstore_pixels = attrs.get('acqstore_pixels')
    if isinstance(acqstore_pixels, dict):
        raw_header = acqstore_pixels.get('header')
        if isinstance(raw_header, dict):
            return _header_from_json_dict(path, raw_header)

    dims = _dims_from_multiscales(attrs, int(arr.ndim))
    shape = tuple(int(x) for x in arr.shape)
    sizes = {dims[i]: shape[i] for i in range(len(dims))}
    dtype = np.dtype(arr.dtype)
    num_channels = int(sizes.get('C', 1))
    physical_units, physical_units_labels = _physical_from_multiscales(attrs, dims)
    return ImageHeader(
        path=str(path),
        shape=shape,
        dims=dims,
        sizes=sizes,
        dtype=dtype,
        num_channels=num_channels,
        num_scenes=1,
        physical_units=physical_units,
        physical_units_labels=physical_units_labels,
        date='',
        time='',
    ).with_coerced_physical_calibration()


def _header_from_json_dict(path: str | Path, raw: dict[str, Any]) -> ImageHeader:
    dims = tuple(str(x).upper() for x in raw.get('dims', ()))
    shape = tuple(int(x) for x in raw.get('shape', ()))
    sizes = {str(k).upper(): int(v) for k, v in dict(raw.get('sizes', {})).items()}
    if not dims:
        dims = _default_dims_for_ndim(len(shape))
    if not sizes:
        sizes = {dims[i]: shape[i] for i in range(len(dims))}
    physical_units = tuple(1.0 if x is None else x for x in raw.get('physical_units', ()))
    physical_units_labels = tuple(str(x) for x in raw.get('physical_units_labels', ()))
    return ImageHeader(
        path=str(path),
        shape=shape,
        dims=dims,
        sizes=sizes,
        dtype=np.dtype(str(raw.get('dtype', 'uint8'))),
        num_channels=int(raw.get('num_channels', sizes.get('C', 1))),
        num_scenes=1,
        physical_units=physical_units,
        physical_units_labels=physical_units_labels,
        date=str(raw.get('date', '')),
        time=str(raw.get('time', '')),
        file_size=str(raw.get('file_size', '')),
    ).with_coerced_physical_calibration()


def _dims_from_multiscales(attrs: dict[str, Any], ndim: int) -> tuple[str, ...]:
    multiscales = attrs.get('multiscales')
    if isinstance(multiscales, list) and multiscales and isinstance(multiscales[0], dict):
        axes = multiscales[0].get('axes')
        if isinstance(axes, list) and len(axes) == ndim:
            names: list[str] = []
            for axis in axes:
                if isinstance(axis, dict) and isinstance(axis.get('name'), str):
                    names.append(str(axis['name']).upper())
            if len(names) == ndim:
                return tuple(names)
    return _default_dims_for_ndim(ndim)


def _default_dims_for_ndim(ndim: int) -> tuple[str, ...]:
    if ndim == 2:
        return ('Y', 'X')
    if ndim == 3:
        return ('Z', 'Y', 'X')
    if ndim == 4:
        return ('C', 'Z', 'Y', 'X')
    if ndim == 5:
        return ('T', 'C', 'Z', 'Y', 'X')
    raise ValueError(f'Unsupported OME-Zarr array rank {ndim}; expected 2-5')


def _physical_from_multiscales(
    attrs: dict[str, Any],
    dims: tuple[str, ...],
) -> tuple[tuple[float, ...], tuple[str, ...]]:
    units = [1.0 for _ in dims]
    labels = ['Pixels' for _ in dims]
    multiscales = attrs.get('multiscales')
    if isinstance(multiscales, list) and multiscales and isinstance(multiscales[0], dict):
        axes = multiscales[0].get('axes')
        if isinstance(axes, list):
            for i, axis in enumerate(axes[: len(dims)]):
                if isinstance(axis, dict) and axis.get('unit'):
                    labels[i] = str(axis['unit'])
        datasets = multiscales[0].get('datasets')
        if isinstance(datasets, list) and datasets and isinstance(datasets[0], dict):
            txs = datasets[0].get('coordinateTransformations')
            if isinstance(txs, list):
                for tx in txs:
                    if isinstance(tx, dict) and tx.get('type') == 'scale':
                        scale = tx.get('scale')
                        if isinstance(scale, list) and len(scale) == len(dims):
                            for i, value in enumerate(scale):
                                try:
                                    units[i] = float(value)
                                except (TypeError, ValueError):
                                    units[i] = 1.0
                            break
    return tuple(units), tuple(labels)
