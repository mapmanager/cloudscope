"""Open acquisition files into transport-neutral API v2 models."""

from __future__ import annotations

from pathlib import Path
from collections.abc import Sequence

import numpy as np

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.supported_import_extensions import (
    normalize_import_extension_for_path,
)
from acqstore.acq_image.file_loaders.base_file_loader import ReferenceImage
from acqstore_server.v2.models import (
    AcquisitionHeader,
    AxisInfo,
    ChannelPlane,
    OpenedAcquisition,
    ReferenceChannelPlane,
    ReferenceImageData,
    ScanPath,
)


class OpenServiceError(Exception):
    """Domain error with a stable machine-readable API v2 code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _format_from_path(path: Path) -> str:
    """Return AcqStore's canonical simple or compound import extension."""
    return normalize_import_extension_for_path(path) or 'unknown'


def _channel_name(index: int) -> str:
    return f'CH{index + 1}'


def _validate_plane(array: np.ndarray, *, label: str) -> np.ndarray:
    plane = np.asarray(array)
    if plane.ndim != 2:
        raise OpenServiceError(
            'decode_failed',
            f'Expected {label} to be a 2-D (Y, X) plane, got shape {plane.shape}',
        )
    return plane


def _validate_channel_indices(
    requested: Sequence[int] | None,
    *,
    num_channels: int,
) -> tuple[int, ...]:
    if requested is None:
        return tuple(range(num_channels))

    indices = tuple(int(index) for index in requested)
    if not indices:
        raise OpenServiceError(
            'invalid_channel_indices',
            'channelIndices must not be empty',
        )
    if any(index < 0 for index in indices):
        raise OpenServiceError(
            'invalid_channel_indices',
            f'channelIndices must contain only non-negative integers: {list(indices)!r}',
        )
    if len(set(indices)) != len(indices):
        raise OpenServiceError(
            'invalid_channel_indices',
            f'channelIndices must not contain duplicates: {list(indices)!r}',
        )
    out_of_range = [index for index in indices if index >= num_channels]
    if out_of_range:
        raise OpenServiceError(
            'channel_out_of_range',
            f'channelIndices {out_of_range!r} out of range for numChannels={num_channels}',
        )
    return indices



def _header_from_acq(acq: AcqImage) -> AcquisitionHeader:
    """Return AcqStore's JSON-safe normalized image header."""
    header = acq.images.header.as_json_dict()
    return AcquisitionHeader(
        shape=tuple(int(value) for value in header['shape']),
        dims=tuple(str(value) for value in header['dims']),
        sizes={str(key): int(value) for key, value in header['sizes'].items()},
        dtype=str(header['dtype']),
        num_channels=int(header['num_channels']),
        physical_units=tuple(
            None if value is None else float(value)
            for value in header['physical_units']
        ),
        physical_units_labels=tuple(str(value) for value in header['physical_units_labels']),
        date=str(header['date']),
        time=str(header['time']),
        file_size=str(header['file_size']),
    )

def _axis_info_from_acq(
    acq: AcqImage,
    *,
    shape: tuple[int, int],
) -> tuple[AxisInfo, AxisInfo]:
    try:
        step_y, step_x = acq.get_image_physical_units()
    except ValueError as exc:
        raise OpenServiceError('calibration_unavailable', str(exc)) from exc

    steps = (float(step_y), float(step_x))
    if any(not np.isfinite(step) or step <= 0 for step in steps):
        raise OpenServiceError(
            'calibration_unavailable',
            f'Expected positive finite Y/X physical steps, got {steps!r}',
        )

    header = acq.images.header
    dims = tuple(header.dims)
    labels = tuple(header.physical_units_labels)
    try:
        y_index = dims.index('Y')
        x_index = dims.index('X')
    except ValueError as exc:
        raise OpenServiceError(
            'calibration_unavailable',
            f'Expected header dims to include Y and X; got dims={dims!r}',
        ) from exc

    y_unit = str(labels[y_index]).strip() if y_index < len(labels) else ''
    x_unit = str(labels[x_index]).strip() if x_index < len(labels) else ''
    if not y_unit or not x_unit:
        raise OpenServiceError(
            'calibration_unavailable',
            f'Expected non-empty Y/X physical unit labels; got {(y_unit, x_unit)!r}',
        )

    return (
        AxisInfo(array_dimension=0, name='Y', size=shape[0], step=steps[0], unit=y_unit),
        AxisInfo(array_dimension=1, name='X', size=shape[1], step=steps[1], unit=x_unit),
    )


def _reference_axes(
    reference: ReferenceImage,
    *,
    shape: tuple[int, int],
) -> tuple[AxisInfo, AxisInfo]:
    try:
        plane = reference.get_plane(0)
    except (ValueError, NotImplementedError) as exc:
        raise OpenServiceError('decode_failed', f'Reference image: {exc}') from exc

    steps = (float(plane.dx), float(plane.dy))
    units = (str(plane.x_unit).strip(), str(plane.y_unit).strip())
    if any(not np.isfinite(step) or step <= 0 for step in steps):
        raise OpenServiceError(
            'calibration_unavailable',
            f'Expected positive finite reference Y/X steps, got {steps!r}',
        )
    if not units[0] or not units[1]:
        raise OpenServiceError(
            'calibration_unavailable',
            f'Expected non-empty reference Y/X units, got {units!r}',
        )
    return (
        AxisInfo(array_dimension=0, name='Y', size=shape[0], step=steps[0], unit=units[0]),
        AxisInfo(array_dimension=1, name='X', size=shape[1], step=steps[1], unit=units[1]),
    )


def _scan_path(reference: ReferenceImage) -> ScanPath | None:
    try:
        plot = reference.get_scan_path_plot()
    except ValueError as exc:
        raise OpenServiceError('decode_failed', f'Reference scan path: {exc}') from exc
    if plot is None:
        return None
    x_values, y_values = plot
    return ScanPath(
        x=tuple(float(value) for value in np.asarray(x_values).ravel()),
        y=tuple(float(value) for value in np.asarray(y_values).ravel()),
    )


def _reference_data(reference: ReferenceImage | None) -> ReferenceImageData | None:
    if reference is None:
        return None

    channels: list[ReferenceChannelPlane] = []
    expected_shape: tuple[int, int] | None = None
    for index in range(int(reference.num_channels)):
        try:
            display_plane = reference.get_plane(index)
        except (ValueError, NotImplementedError) as exc:
            raise OpenServiceError('decode_failed', f'Reference channel {index}: {exc}') from exc
        plane = _validate_plane(display_plane.array, label=f'reference channel {index}')
        shape = (int(plane.shape[0]), int(plane.shape[1]))
        if expected_shape is None:
            expected_shape = shape
        elif shape != expected_shape:
            raise OpenServiceError(
                'decode_failed',
                f'Reference channel shapes differ: expected {expected_shape}, got {shape}',
            )
        channels.append(
            ReferenceChannelPlane(
                index=index,
                source_dtype=str(plane.dtype),
                array=plane,
            )
        )

    if not channels or expected_shape is None:
        raise OpenServiceError('decode_failed', 'Reference image contains no channels')

    line_roi = None
    if reference.line_roi is not None:
        line_roi = tuple(float(value) for value in reference.line_roi)

    return ReferenceImageData(
        axes=_reference_axes(reference, shape=expected_shape),
        channels=tuple(channels),
        line_roi=line_roi,
        scan_path=_scan_path(reference),
    )


def open_acquisition(
    path: str,
    *,
    channel_indices: Sequence[int] | None = None,
) -> OpenedAcquisition:
    """Open one file and return generic selected 2-D channel planes.

    Args:
        path: Filesystem path to an acquisition supported by AcqStore.
        channel_indices: Optional ordered source-channel indices. ``None`` loads
            all available channels.

    Returns:
        Transport-neutral acquisition data. Arrays preserve their source dtype.

    Raises:
        OpenServiceError: For path, format, channel, calibration, or decoding
            failures.
    """
    if not path or not str(path).strip():
        raise OpenServiceError('path_required', 'path is required')

    resolved = Path(path).expanduser().resolve(strict=False)
    if not resolved.exists():
        raise OpenServiceError('path_not_found', f'Acquisition path not found: {resolved}')

    try:
        acq = AcqImage(str(resolved), load_images=True, load_analysis_csv=False)
    except ValueError as exc:
        raise OpenServiceError('unsupported_format', str(exc)) from exc
    except OSError as exc:
        raise OpenServiceError('decode_failed', str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - normalize third-party loader errors
        raise OpenServiceError('decode_failed', f'{type(exc).__name__}: {exc}') from exc

    try:
        pixels = acq.pixels
    except RuntimeError as exc:
        raise OpenServiceError('decode_failed', str(exc)) from exc

    num_channels = int(pixels.num_channels)
    indices = _validate_channel_indices(channel_indices, num_channels=num_channels)

    channels: list[ChannelPlane] = []
    expected_shape: tuple[int, int] | None = None
    source_dtype: str | None = None
    for index in indices:
        try:
            plane = _validate_plane(
                pixels.get_plane(c=index),
                label=f'channel {index}',
            )
        except (IndexError, ValueError) as exc:
            raise OpenServiceError('channel_out_of_range', str(exc)) from exc
        shape = (int(plane.shape[0]), int(plane.shape[1]))
        if expected_shape is None:
            expected_shape = shape
        elif shape != expected_shape:
            raise OpenServiceError(
                'decode_failed',
                f'Channel shapes differ: expected {expected_shape}, got {shape}',
            )
        plane_dtype = str(plane.dtype)
        if source_dtype is None:
            source_dtype = plane_dtype
        elif plane_dtype != source_dtype:
            raise OpenServiceError(
                'decode_failed',
                f'Channel dtypes differ: expected {source_dtype}, got {plane_dtype}',
            )
        channels.append(
            ChannelPlane(
                index=index,
                name=_channel_name(index),
                source_dtype=plane_dtype,
                array=plane,
            )
        )

    if not channels or expected_shape is None or source_dtype is None:
        raise OpenServiceError('decode_failed', 'No source channels were selected')

    reference: ReferenceImage | None = None
    loader = acq.images
    if loader.has_reference_image:
        reference = loader.reference_image

    return OpenedAcquisition(
        path=resolved,
        format=_format_from_path(resolved),
        source_dtype=source_dtype,
        num_source_channels=num_channels,
        header=_header_from_acq(acq),
        axes=_axis_info_from_acq(acq, shape=expected_shape),
        channels=tuple(channels),
        reference=_reference_data(reference),
    )
