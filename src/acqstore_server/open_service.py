"""Open acquisition files via AcqImage and build API payloads."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.file_loaders.base_file_loader import ReferenceImage
from acqstore_server.logging_setup import get_logger
from acqstore_server.schemas import (
    CalibrationMeta,
    ChannelMeta,
    ChannelsMeta,
    OpenSuccess,
    ReferenceChannelMeta,
    ReferenceMeta,
    ScanPathMeta,
    SourceMeta,
)
from acqstore_server.session_store import SessionBuffers, SessionStore

logger = get_logger('open_service')


class OpenServiceError(Exception):
    """Domain error mapped to API ``error`` codes.

    Args:
        code: Stable machine-readable code (e.g. ``path_not_found``).
        message: Human-readable detail.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _format_from_path(path: str) -> str:
    suffix = Path(path).suffix.lower().lstrip('.')
    if suffix == 'tiff':
        return 'tif'
    return suffix or 'unknown'


def _channel_name(index: int) -> str:
    return f'CH{index + 1}'


def _plane_to_f32_le(plane: np.ndarray) -> tuple[bytes, int, int]:
    """Convert a ``(Y, X)`` plane to row-major float32 LE bytes.

    Args:
        plane: Two-dimensional array.

    Returns:
        ``(bytes, height, width)``.

    Raises:
        OpenServiceError: If ``plane`` is not 2-D.
    """
    arr = np.asarray(plane)
    if arr.ndim != 2:
        raise OpenServiceError(
            'decode_failed',
            f'Expected a 2-D (Y, X) plane, got shape {arr.shape}',
        )
    height, width = int(arr.shape[0]), int(arr.shape[1])
    f32 = np.ascontiguousarray(arr, dtype=np.float32)
    return f32.tobytes(order='C'), height, width


def _calibration_from_acq(acq: AcqImage) -> CalibrationMeta:
    """Map AcqImage physical units to HTML calibration fields.

    Existing HTML aliases (``msPerLine``, ``umPerPixel``, …) are preserved.
    Additive ``dim_0_*`` / ``dim_1_*`` fields expose the served 2-D plane
    (rows/Y, columns/X) steps and physical unit labels from the header.

    Args:
        acq: Loaded acquisition.

    Returns:
        Calibration metadata.

    Raises:
        OpenServiceError: If units are missing or non-finite.
    """
    try:
        step_y, step_x = acq.get_image_physical_units()
    except ValueError as exc:
        raise OpenServiceError('calibration_unavailable', str(exc)) from exc

    step_y_f = float(step_y)
    step_x_f = float(step_x)
    if not np.isfinite(step_y_f) or not np.isfinite(step_x_f):
        raise OpenServiceError(
            'calibration_unavailable',
            f'Non-finite physical units: step_y={step_y_f!r}, step_x={step_x_f!r}',
        )
    if step_y_f <= 0 or step_x_f <= 0:
        raise OpenServiceError(
            'calibration_unavailable',
            f'Non-positive physical units: step_y={step_y_f!r}, step_x={step_x_f!r}',
        )

    header = acq.images.header
    dims = header.dims
    try:
        i_y = dims.index('Y')
        i_x = dims.index('X')
    except ValueError as exc:
        raise OpenServiceError(
            'calibration_unavailable',
            f'Expected header dims to include Y and X; got dims={dims!r}',
        ) from exc
    labels = header.physical_units_labels
    dim_0_units = str(labels[i_y]) if i_y < len(labels) else 'Pixels'
    dim_1_units = str(labels[i_x]) if i_x < len(labels) else 'Pixels'
    if not dim_0_units.strip():
        dim_0_units = 'Pixels'
    if not dim_1_units.strip():
        dim_1_units = 'Pixels'

    return {
        'msPerLine': step_y_f * 1000.0,
        'umPerPixel': step_x_f,
        'stepYSeconds': step_y_f,
        'stepXUm': step_x_f,
        'unitsSource': 'acqimage',
        'dim_0_step': step_y_f,
        'dim_1_step': step_x_f,
        'dim_0_units': dim_0_units,
        'dim_1_units': dim_1_units,
    }


def _channel_meta(
    *,
    index: int,
    role: str,
    height: int,
    width: int,
    session_id: str,
) -> ChannelMeta:
    byte_length = height * width * 4
    return {
        'index': index,
        'name': _channel_name(index),
        'role': role,  # type: ignore[typeddict-item]
        'encoding': 'raw-f32-le',
        'layout': 'row-major',
        'height': height,
        'width': width,
        'byteLength': byte_length,
        'url': f'/api/v1/session/{session_id}/channel/{role}',
    }


def _scan_path_meta(ref: ReferenceImage) -> ScanPathMeta | None:
    """Serialize scan path for JSON clients."""
    try:
        plot = ref.get_scan_path_plot()
    except ValueError:
        return None
    if plot is None:
        return None
    x_pixels, y_pixels = plot
    return {
        'x': [float(v) for v in np.asarray(x_pixels).ravel().tolist()],
        'y': [float(v) for v in np.asarray(y_pixels).ravel().tolist()],
    }


def open_path(
    path: str,
    store: SessionStore,
    *,
    calcium_channel: int = 0,
    vessel_channel: int | None = 1,
) -> OpenSuccess:
    """Open ``path`` with AcqImage and register channel/reference bytes in ``store``.

    Args:
        path: Absolute or expandable filesystem path.
        store: Session store for binary GETs.
        calcium_channel: Zero-based calcium channel index.
        vessel_channel: Zero-based vessel channel index, or ``None`` to force
            single-channel even when more channels exist. When the file has
            fewer than two channels, vessels are omitted regardless.

    Returns:
        Open success payload including optional ``reference``.

    Raises:
        OpenServiceError: On path/format/channel/decode/calibration failures.
    """
    if not path or not str(path).strip():
        raise OpenServiceError('path_not_found', 'path is required')

    resolved = Path(path).expanduser().resolve(strict=False)
    if not resolved.is_file():
        raise OpenServiceError('path_not_found', f'File not found: {resolved}')

    if calcium_channel < 0:
        raise OpenServiceError(
            'channel_out_of_range',
            f'calciumChannel must be >= 0, got {calcium_channel}',
        )
    if vessel_channel is not None and vessel_channel < 0:
        raise OpenServiceError(
            'channel_out_of_range',
            f'vesselChannel must be >= 0 or null, got {vessel_channel}',
        )

    t0 = time.perf_counter()
    logger.info('Opening %s (calcium=%s vessels=%s)', resolved, calcium_channel, vessel_channel)

    try:
        acq = AcqImage(str(resolved), load_images=True, load_analysis_csv=False)
    except ValueError as exc:
        raise OpenServiceError('unsupported_format', str(exc)) from exc
    except OSError as exc:
        raise OpenServiceError('decode_failed', str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — map unknown loader failures
        raise OpenServiceError('decode_failed', f'{type(exc).__name__}: {exc}') from exc

    try:
        pixels = acq.pixels
    except RuntimeError as exc:
        raise OpenServiceError('decode_failed', str(exc)) from exc

    num_channels = int(pixels.num_channels)
    if calcium_channel >= num_channels:
        raise OpenServiceError(
            'channel_out_of_range',
            f'calciumChannel={calcium_channel} out of range for numChannels={num_channels}',
        )

    try:
        calcium_plane = pixels.get_plane(c=calcium_channel)
    except (IndexError, ValueError) as exc:
        raise OpenServiceError('channel_out_of_range', str(exc)) from exc

    calcium_bytes, height, width = _plane_to_f32_le(calcium_plane)
    vessels_bytes: bytes | None = None
    vessels_index: int | None = None

    include_vessels = (
        num_channels >= 2
        and vessel_channel is not None
        and vessel_channel < num_channels
        and vessel_channel != calcium_channel
    )
    if num_channels >= 2 and vessel_channel is not None and vessel_channel >= num_channels:
        raise OpenServiceError(
            'channel_out_of_range',
            f'vesselChannel={vessel_channel} out of range for numChannels={num_channels}',
        )
    if include_vessels:
        assert vessel_channel is not None
        try:
            vessels_plane = pixels.get_plane(c=vessel_channel)
        except (IndexError, ValueError) as exc:
            raise OpenServiceError('channel_out_of_range', str(exc)) from exc
        vessels_bytes, v_h, v_w = _plane_to_f32_le(vessels_plane)
        if v_h != height or v_w != width:
            raise OpenServiceError(
                'decode_failed',
                f'Channel shapes differ: calcium {width}x{height}, vessels {v_w}x{v_h}',
            )
        vessels_index = int(vessel_channel)

    calibration = _calibration_from_acq(acq)

    # Build all reference channel planes before create(); URLs need session id.
    ref_channel_bytes: list[bytes] = []
    ref_channel_partials: list[dict[str, Any]] = []
    ref_shared: dict[str, Any] | None = None
    try:
        if acq.images.has_reference_image:
            ref_obj = acq.images.reference_image
            if ref_obj is not None:
                n_ref = max(1, int(ref_obj.num_channels))
                line_roi = ref_obj.get_line_roi()
                ref_shared = {
                    'lineRoi': (
                        [float(v) for v in line_roi] if line_roi is not None else None
                    ),
                    'scanPath': _scan_path_meta(ref_obj),
                }
                for c_idx in range(n_ref):
                    plane = ref_obj.get_plane(channel=c_idx)
                    plane_bytes, r_h, r_w = _plane_to_f32_le(plane.array)
                    ref_channel_bytes.append(plane_bytes)
                    ref_channel_partials.append(
                        {
                            'index': c_idx,
                            'height': r_h,
                            'width': r_w,
                            'dx': float(plane.dx),
                            'dy': float(plane.dy),
                            'xUnit': str(plane.x_unit),
                            'yUnit': str(plane.y_unit),
                        }
                    )
                if ref_channel_partials:
                    # All reference planes share H×W; reject drift early.
                    h0 = int(ref_channel_partials[0]['height'])
                    w0 = int(ref_channel_partials[0]['width'])
                    for part in ref_channel_partials[1:]:
                        if int(part['height']) != h0 or int(part['width']) != w0:
                            raise OpenServiceError(
                                'decode_failed',
                                'Reference channel shapes differ across channels',
                            )
    except OpenServiceError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning('Reference image unavailable for %s: %s', resolved, exc)
        ref_channel_bytes = []
        ref_channel_partials = []
        ref_shared = None

    session_id = store.create(
        SessionBuffers(
            calcium=calcium_bytes,
            vessels=vessels_bytes,
            reference_channels=tuple(ref_channel_bytes),
        )
    )

    reference: ReferenceMeta | None = None
    if ref_channel_partials and ref_shared is not None:
        channels_meta: list[ReferenceChannelMeta] = []
        for part in ref_channel_partials:
            idx = int(part['index'])
            h = int(part['height'])
            w = int(part['width'])
            channels_meta.append(
                {
                    'index': idx,
                    'encoding': 'raw-f32-le',
                    'layout': 'row-major',
                    'height': h,
                    'width': w,
                    'byteLength': h * w * 4,
                    'url': f'/api/v1/session/{session_id}/reference/channel/{idx}',
                    'dx': float(part['dx']),
                    'dy': float(part['dy']),
                    'xUnit': str(part['xUnit']),
                    'yUnit': str(part['yUnit']),
                }
            )
        ch0 = channels_meta[0]
        reference = {
            'numChannels': len(channels_meta),
            'encoding': 'raw-f32-le',
            'layout': 'row-major',
            'height': ch0['height'],
            'width': ch0['width'],
            'byteLength': ch0['byteLength'],
            'channels': channels_meta,
            'lineRoi': ref_shared['lineRoi'],
            'scanPath': ref_shared['scanPath'],
            'dx': ch0['dx'],
            'dy': ch0['dy'],
            'xUnit': ch0['xUnit'],
            'yUnit': ch0['yUnit'],
        }

    channels: ChannelsMeta = {
        'calcium': _channel_meta(
            index=calcium_channel,
            role='calcium',
            height=height,
            width=width,
            session_id=session_id,
        ),
    }
    if vessels_bytes is not None and vessels_index is not None:
        channels['vessels'] = _channel_meta(
            index=vessels_index,
            role='vessels',
            height=height,
            width=width,
            session_id=session_id,
        )

    source: SourceMeta = {
        'path': str(resolved),
        'format': _format_from_path(str(resolved)),
        'numChannels': num_channels,
        'width': width,
        'height': height,
        'dtype': 'float32',
    }

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    try:
        dims_display = acq.images.header.format_dims_display()
    except Exception:  # noqa: BLE001 — logging must not fail open
        dims_display = '?'
    try:
        header_shape = tuple(int(v) for v in acq.images.header.shape)
    except Exception:  # noqa: BLE001
        header_shape = ()
    step_y = float(calibration['stepYSeconds'])
    step_x = float(calibration['stepXUm'])
    vessels_summary = (
        f'[{vessels_index}]={height}x{width}'
        if vessels_index is not None
        else 'omit'
    )
    logger.info('Opened %s in %.1f ms', resolved.name, elapsed_ms)
    logger.info('  dims=%s', dims_display)
    logger.info('  shape=%s C=%s', header_shape, num_channels)
    logger.info(
        '  calcium[%s]=%sx%s vessels=%s',
        calcium_channel,
        height,
        width,
        vessels_summary,
    )
    logger.info(
        '  msPerLine=%.6g umPerPixel=%.6g',
        float(calibration['msPerLine']),
        float(calibration['umPerPixel']),
    )
    logger.info('  units stepY=%.6gs stepX=%.6g um', step_y, step_x)
    if reference is None:
        logger.info('  reference=none')
    else:
        logger.info(
            '  reference=channels=%s %sx%s',
            reference['numChannels'],
            reference['height'],
            reference['width'],
        )
        # ReferenceImagePlane: dx → row/Y step, dy → column/X step.
        logger.info(
            '  reference units stepY=%.6g %s stepX=%.6g %s',
            float(reference['dx']),
            reference.get('yUnit') or 'um',
            float(reference['dy']),
            reference.get('xUnit') or 'um',
        )
        if reference['lineRoi'] is not None:
            logger.info('  reference lineRoi=%s', reference['lineRoi'])

    return {
        'ok': True,
        'sessionId': session_id,
        'source': source,
        'calibration': calibration,
        'channels': channels,
        'reference': reference,
    }


def parse_channel_overrides(body: dict[str, Any] | None) -> tuple[int, int | None]:
    """Parse optional channel indices from a request body.

    Args:
        body: JSON object or ``None``.

    Returns:
        ``(calcium_channel, vessel_channel)``. Defaults are ``0`` and ``1``.

    Raises:
        OpenServiceError: If channel fields are not ints / null.
    """
    data = body or {}
    calcium_raw = data.get('calciumChannel', 0)
    vessel_raw = data.get('vesselChannel', 1)

    try:
        calcium_channel = int(calcium_raw)
    except (TypeError, ValueError) as exc:
        raise OpenServiceError(
            'channel_out_of_range',
            f'calciumChannel must be an int, got {calcium_raw!r}',
        ) from exc

    if vessel_raw is None:
        vessel_channel: int | None = None
    else:
        try:
            vessel_channel = int(vessel_raw)
        except (TypeError, ValueError) as exc:
            raise OpenServiceError(
                'channel_out_of_range',
                f'vesselChannel must be an int or null, got {vessel_raw!r}',
            ) from exc

    return calcium_channel, vessel_channel


def parse_open_request(body: dict[str, Any] | None) -> tuple[str, int, int | None]:
    """Parse and validate an open request body.

    Args:
        body: JSON object or ``None``.

    Returns:
        ``(path, calcium_channel, vessel_channel)``.

    Raises:
        OpenServiceError: If required fields are invalid.
    """
    data = body or {}
    path = data.get('path')
    if not isinstance(path, str) or not path.strip():
        raise OpenServiceError('path_not_found', 'JSON body must include string "path"')
    calcium_channel, vessel_channel = parse_channel_overrides(data)
    return path, calcium_channel, vessel_channel


def parse_pick_extensions(body: dict[str, Any] | None) -> list[str] | None:
    """Return optional ``extensions`` list from a pick-and-open body.

    Args:
        body: JSON object or ``None``.

    Returns:
        List of extension strings, or ``None`` when omitted.
    """
    data = body or {}
    raw = data.get('extensions')
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise OpenServiceError(
            'unsupported_format',
            f'extensions must be a list of strings, got {type(raw).__name__}',
        )
    return [str(item) for item in raw]
