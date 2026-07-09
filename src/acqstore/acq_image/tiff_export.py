"""TIFF export helpers for :class:`acqstore.acq_image.acq_image.AcqImage`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from .acq_pixels import AcqPixels


def save_pixels_as_tif(
    pixels: AcqPixels,
    path: str | Path,
    *,
    imagej_metadata: bool = True,
    overwrite: bool = False,
) -> None:
    """Write full pixel data to a standard TIFF file with optional ImageJ metadata.

    Args:
        pixels: Pixel data to export. The full array is materialized before
            writing because TIFF export is an eager file export path.
        path: Destination TIFF filename. The caller must provide the complete
            filename.
        imagej_metadata: When true, request ImageJ-compatible metadata from
            :mod:`tifffile` for physical X/Y scale, unit, and frame interval when
            those values are available from the image header.
        overwrite: Whether to replace an existing TIFF file.

    Raises:
        FileExistsError: If ``path`` exists and ``overwrite`` is false.
        ValueError: If ``path`` is empty or names a directory.
        ImportError: If :mod:`tifffile` is not installed.
    """
    try:
        import tifffile
    except ImportError as exc:  # pragma: no cover - project dependency
        raise ImportError('TIFF export requires tifffile') from exc

    dest = Path(path)
    if not str(dest):
        raise ValueError('TIFF export requires an explicit destination filename')
    if dest.exists():
        if dest.is_dir():
            raise ValueError(f'TIFF destination is a directory: {dest}')
        if not overwrite:
            raise FileExistsError(f'TIFF destination already exists: {dest}')
    dest.parent.mkdir(parents=True, exist_ok=True)

    data = np.asarray(pixels.get_array(0))
    metadata = _build_tifffile_metadata(pixels, imagej_metadata=imagej_metadata)
    tifffile.imwrite(
        dest,
        data,
        imagej=bool(imagej_metadata),
        metadata=metadata,
    )


def _build_tifffile_metadata(
    pixels: AcqPixels,
    *,
    imagej_metadata: bool,
) -> dict[str, Any]:
    """Return tifffile metadata for the exported array.

    Args:
        pixels: Pixel object being exported.
        imagej_metadata: Whether to include ImageJ-specific keys.

    Returns:
        Metadata dictionary for :func:`tifffile.imwrite`.
    """
    metadata: dict[str, Any] = {'axes': ''.join(pixels.axes)}
    if not imagej_metadata:
        return metadata

    unit = _common_spatial_unit(pixels)
    if unit is not None:
        metadata['unit'] = unit
    spacing = _spacing_for_dim(pixels, 'Z')
    if spacing is not None:
        metadata['spacing'] = spacing
    frame_interval = _spacing_for_dim(pixels, 'T')
    if frame_interval is not None:
        metadata['finterval'] = frame_interval
    return metadata


def _spacing_for_dim(pixels: AcqPixels, dim: str) -> float | None:
    if dim not in pixels.axes:
        return None
    index = pixels.axes.index(dim)
    try:
        value = float(pixels.header.physical_units[index])
    except (IndexError, TypeError, ValueError):
        return None
    if value <= 0.0:
        return None
    return value


def _common_spatial_unit(pixels: AcqPixels) -> str | None:
    labels: list[str] = []
    for dim in ('Y', 'X'):
        if dim not in pixels.axes:
            continue
        index = pixels.axes.index(dim)
        if index < len(pixels.header.physical_units_labels):
            label = str(pixels.header.physical_units_labels[index])
            if label and label.lower() != 'pixels':
                labels.append(_imagej_unit_label(label))
    if not labels:
        return None
    first = labels[0]
    if all(label == first for label in labels):
        return first
    return first


def _imagej_unit_label(label: str) -> str:
    normalized = label.strip()
    low = normalized.lower()
    if low in {'micrometer', 'micrometers', 'micron', 'microns', 'µm'}:
        return 'um'
    if low in {'second', 'seconds'}:
        return 'sec'
    return normalized
