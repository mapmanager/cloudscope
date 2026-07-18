"""Internal transport-neutral models for AcqStore Server API v2.

These models use Python ``snake_case`` names and intentionally contain no
HTTP URLs, JSON aliases, FastAPI types, or client-specific display semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True, slots=True)
class AxisInfo:
    """One array axis for a served two-dimensional plane."""

    array_dimension: int
    name: str
    size: int
    step: float
    unit: str


@dataclass(frozen=True, slots=True)
class ChannelPlane:
    """One selected source channel as a two-dimensional NumPy plane."""

    index: int
    name: str
    source_dtype: str
    array: np.ndarray


@dataclass(frozen=True, slots=True)
class ScanPath:
    """Reference-image scan-path coordinates in AcqStore convention."""

    x: tuple[float, ...]
    y: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class ReferenceChannelPlane:
    """One reference-image channel as a two-dimensional NumPy plane."""

    index: int
    source_dtype: str
    array: np.ndarray


@dataclass(frozen=True, slots=True)
class ReferenceImageData:
    """Generic reference-image data associated with an acquisition."""

    axes: tuple[AxisInfo, AxisInfo]
    channels: tuple[ReferenceChannelPlane, ...]
    line_roi: tuple[float, float, float, float] | None
    scan_path: ScanPath | None


@dataclass(frozen=True, slots=True)
class AcquisitionHeader:
    """Normalized AcqStore image header for thin clients."""

    shape: tuple[int, ...]
    dims: tuple[str, ...]
    sizes: dict[str, int]
    dtype: str
    num_channels: int
    physical_units: tuple[float | None, ...]
    physical_units_labels: tuple[str, ...]
    date: str
    time: str
    file_size: str


@dataclass(frozen=True, slots=True)
class OpenedAcquisition:
    """Transport-neutral result of opening one acquisition file."""

    path: Path
    format: str
    source_dtype: str
    num_source_channels: int
    header: AcquisitionHeader
    axes: tuple[AxisInfo, AxisInfo]
    channels: tuple[ChannelPlane, ...]
    reference: ReferenceImageData | None
