"""FastAPI routes for the independent AcqStore Server API v2."""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Callable, Sequence
from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from acqstore.acq_image.supported_import_extensions import (
    get_allowed_import_extensions,
    get_supported_import_extensions,
)

from acqstore_server.logging_setup import get_logger
from acqstore_server.v2.encoding import encode_raw_f32_le
from acqstore_server.v2.errors import StableValidationRoute
from acqstore_server.v2.models import OpenedAcquisition, ReferenceImageData
from acqstore_server.v2.open_service import OpenServiceError, open_acquisition
from acqstore_server.v2.schemas import (
    ApiIndexResponse,
    ApiLinkResponse,
    AxisResponse,
    CapabilitiesResponse,
    ChannelResponse,
    DeleteSessionResponse,
    ErrorResponse,
    HeaderResponse,
    OpenRequest,
    OpenResponse,
    PickAndOpenRequest,
    PlaneResponse,
    ReferenceChannelResponse,
    ReferenceResponse,
    ScanPathResponse,
    SessionResponse,
    SourceResponse,
)
from acqstore_server.v2.session_store import SessionBuffers, SessionStore

PickFileFn = Callable[[Sequence[str] | None], str | None]
OpenAcquisitionFn = Callable[..., OpenedAcquisition]
DEFAULT_OPEN_LOAD_TIMEOUT_S = 120.0
logger = get_logger('v2.routes')

_ERROR_STATUS: dict[str, int] = {
    'cancelled': 200,
    'path_required': 422,
    'path_not_found': 404,
    'unsupported_format': 415,
    'invalid_channel_indices': 422,
    'channel_out_of_range': 422,
    'calibration_unavailable': 422,
    'load_timeout': 504,
    'decode_failed': 500,
}


def open_load_timeout_s() -> float:
    """Return the configured positive open/decode timeout."""
    raw = os.environ.get('ACQSTORE_SERVER_OPEN_TIMEOUT_S', '').strip()
    if not raw:
        return DEFAULT_OPEN_LOAD_TIMEOUT_S
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_OPEN_LOAD_TIMEOUT_S
    return value if value > 0 else DEFAULT_OPEN_LOAD_TIMEOUT_S


def _error(code: str, message: str, *, status_code: int | None = None) -> JSONResponse:
    body = ErrorResponse(error=code, message=message).model_dump(
        by_alias=True, mode='json', exclude_none=True
    )
    return JSONResponse(body, status_code=status_code or _ERROR_STATUS.get(code, 500))


def _plane_response(
    shape: tuple[int, int],
    axes: Sequence[object],
) -> PlaneResponse:
    return PlaneResponse(
        shape=shape,
        axes=[
            AxisResponse(
                array_dimension=axis.array_dimension,
                name=axis.name,
                size=axis.size,
                step=axis.step,
                unit=axis.unit,
            )
            for axis in axes
        ],
    )


def _reference_response(
    session_id: str,
    reference: ReferenceImageData,
    payloads: dict[int, bytes],
) -> ReferenceResponse:
    first = reference.channels[0]
    shape = (int(first.array.shape[0]), int(first.array.shape[1]))
    scan_path = None
    if reference.scan_path is not None:
        scan_path = ScanPathResponse(
            x=list(reference.scan_path.x),
            y=list(reference.scan_path.y),
        )
    return ReferenceResponse(
        plane=_plane_response(shape, reference.axes),
        channels=[
            ReferenceChannelResponse(
                index=channel.index,
                byte_length=len(payloads[channel.index]),
                data_url=(f'/api/v2/sessions/{session_id}/reference/channels/{channel.index}/data'),
            )
            for channel in reference.channels
        ],
        line_roi=reference.line_roi,
        scan_path=scan_path,
    )


def _register_opened(opened: OpenedAcquisition, store: SessionStore) -> OpenResponse:
    channel_payloads = {channel.index: encode_raw_f32_le(channel.array) for channel in opened.channels}
    reference_payloads: dict[int, bytes] = {}
    if opened.reference is not None:
        reference_payloads = {channel.index: encode_raw_f32_le(channel.array) for channel in opened.reference.channels}
    session_id = store.create(
        SessionBuffers(
            channels=channel_payloads,
            reference_channels=reference_payloads,
        )
    )
    first = opened.channels[0]
    shape = (int(first.array.shape[0]), int(first.array.shape[1]))
    reference = None
    if opened.reference is not None:
        reference = _reference_response(session_id, opened.reference, reference_payloads)
    return OpenResponse(
        session_id=session_id,
        source=SourceResponse(
            path=str(opened.path),
            name=opened.path.name,
            format=opened.format,
            source_dtype=opened.source_dtype,
            num_channels=opened.num_source_channels,
        ),
        header=HeaderResponse(
            shape=list(opened.header.shape),
            dims=list(opened.header.dims),
            sizes=opened.header.sizes,
            dtype=opened.header.dtype,
            num_channels=opened.header.num_channels,
            physical_units=list(opened.header.physical_units),
            physical_units_labels=list(opened.header.physical_units_labels),
            date=opened.header.date,
            time=opened.header.time,
            file_size=opened.header.file_size,
        ),
        plane=_plane_response(shape, opened.axes),
        channels=[
            ChannelResponse(
                index=channel.index,
                name=channel.name,
                byte_length=len(channel_payloads[channel.index]),
                data_url=f'/api/v2/sessions/{session_id}/channels/{channel.index}/data',
            )
            for channel in opened.channels
        ],
        reference=reference,
    )


def _format_axis(axis: object) -> str:
    """Return one compact, human-readable served-axis summary."""
    return (
        f'dim{axis.array_dimension} {axis.name} size={axis.size} '
        f'step={axis.step:.6g} {axis.unit}'
    )


def _log_opened_acquisition(opened: OpenedAcquisition, *, elapsed_ms: float) -> None:
    """Log a readable API v2 acquisition summary without large payload dumps."""
    logger.info('Opened %s in %.1f ms', opened.path.name, elapsed_ms)
    logger.info('  path=%s', opened.path)
    logger.info(
        '  source format=%s dtype=%s channels=%s',
        opened.format,
        opened.source_dtype,
        opened.num_source_channels,
    )
    logger.info('  header dims=%s', opened.header.dims)
    logger.info('  header shape=%s', opened.header.shape)
    logger.info('  header sizes=%s', opened.header.sizes)
    logger.info(
        '  header date=%s time=%s fileSize=%s',
        opened.header.date or '-',
        opened.header.time or '-',
        opened.header.file_size or '-',
    )
    logger.info('  plane shape=%s', tuple(int(v) for v in opened.channels[0].array.shape))
    for axis in opened.axes:
        logger.info('  plane axis %s', _format_axis(axis))
    logger.info(
        '  selected channels=%s',
        [channel.index for channel in opened.channels],
    )
    for channel in opened.channels:
        logger.info(
            '  channel[%s] name=%s shape=%s sourceDtype=%s',
            channel.index,
            channel.name,
            tuple(int(v) for v in channel.array.shape),
            channel.source_dtype,
        )

    reference = opened.reference
    if reference is None:
        logger.info('  reference=none')
        return

    logger.info(
        '  reference channels=%s shape=%s',
        len(reference.channels),
        tuple(int(v) for v in reference.channels[0].array.shape),
    )
    for axis in reference.axes:
        logger.info('  reference axis %s', _format_axis(axis))
    for channel in reference.channels:
        logger.info(
            '  reference channel[%s] shape=%s sourceDtype=%s',
            channel.index,
            tuple(int(v) for v in channel.array.shape),
            channel.source_dtype,
        )
    if reference.line_roi is None:
        logger.info('  reference lineRoi=none')
    else:
        logger.info('  reference lineRoi=%s', reference.line_roi)
    if reference.scan_path is None:
        logger.info('  reference scanPath=none')
    else:
        logger.info(
            '  reference scanPath points=%s',
            len(reference.scan_path.x),
        )


async def _open_threaded(
    path: str,
    channel_indices: Sequence[int] | None,
    *,
    open_fn: OpenAcquisitionFn,
) -> OpenedAcquisition:
    timeout_s = open_load_timeout_s()
    started = time.perf_counter()
    try:
        opened = await asyncio.wait_for(
            asyncio.to_thread(open_fn, path, channel_indices=channel_indices),
            timeout=timeout_s,
        )
    except TimeoutError as exc:
        raise OpenServiceError(
            'load_timeout',
            f'Open/decode exceeded {timeout_s:g}s for path: {path}',
        ) from exc
    _log_opened_acquisition(
        opened,
        elapsed_ms=(time.perf_counter() - started) * 1000.0,
    )
    return opened


def create_router(
    *,
    store: SessionStore,
    pick_file: PickFileFn,
    open_fn: OpenAcquisitionFn = open_acquisition,
) -> APIRouter:
    """Create the API v2 router with injected session storage and file picker."""
    router = APIRouter(
        prefix='/api/v2',
        tags=['API v2'],
        route_class=StableValidationRoute,
    )

    @router.get(
        '',
        response_model=ApiIndexResponse,
        summary='Discover API v2 resources',
        description=(
            'Return stable links to the API v2 health, capabilities, OpenAPI, '
            'interactive documentation, and maintained browser demo resources.'
        ),
    )
    def api_index() -> ApiIndexResponse:
        return ApiIndexResponse(
            description=(
                'General-purpose local HTTP API for opening AcqStore-supported '
                'acquisition files and serving generic two-dimensional channel planes.'
            ),
            links={
                'health': ApiLinkResponse(
                    href='/api/v2/health',
                    method='GET',
                    description='Lightweight process and API-version health check.',
                ),
                'capabilities': ApiLinkResponse(
                    href='/api/v2/capabilities',
                    method='GET',
                    description='Runtime import formats, binary encoding, and session TTL.',
                ),
                'open': ApiLinkResponse(
                    href='/api/v2/open',
                    method='POST',
                    description='Open a server-visible acquisition path.',
                ),
                'pickAndOpen': ApiLinkResponse(
                    href='/api/v2/pick-and-open',
                    method='POST',
                    description='Open an acquisition selected with the native file picker.',
                ),
                'openapi': ApiLinkResponse(
                    href='/openapi.json',
                    method='GET',
                    description='Machine-readable OpenAPI document.',
                ),
                'docs': ApiLinkResponse(
                    href='/docs',
                    method='GET',
                    description='Interactive Swagger UI.',
                ),
                'demo': ApiLinkResponse(
                    href='/demo/v2/',
                    method='GET',
                    description='Maintained browser JavaScript client.',
                ),
            },
        )

    @router.get(
        '/health',
        summary='Check API v2 health',
        description='Return a lightweight success response without opening a file.',
    )
    def health() -> dict[str, object]:
        return {'ok': True, 'apiVersion': 'v2'}

    @router.get(
        '/capabilities',
        response_model=CapabilitiesResponse,
        summary='Describe runtime capabilities',
        description=(
            'Return AcqStore import extensions currently available to the server, the binary plane encoding, and the in-memory session TTL.'
        ),
    )
    def capabilities() -> CapabilitiesResponse:
        return CapabilitiesResponse(
            supported_import_extensions=list(get_supported_import_extensions()),
            allowed_import_extensions=list(get_allowed_import_extensions()),
            session_ttl_seconds=store.ttl_seconds,
        )

    @router.post(
        '/open',
        response_model=OpenResponse,
        summary='Open an acquisition path',
        description=(
            'Open a path visible to the local server process, select generic channel indices, and create a temporary binary-data session.'
        ),
        responses={
            404: {'model': ErrorResponse},
            415: {'model': ErrorResponse},
            422: {'model': ErrorResponse},
            500: {'model': ErrorResponse},
            504: {'model': ErrorResponse},
        },
    )
    async def open_endpoint(request: OpenRequest) -> OpenResponse | JSONResponse:
        try:
            opened = await _open_threaded(
                request.path,
                request.channel_indices,
                open_fn=open_fn,
            )
            return _register_opened(opened, store)
        except OpenServiceError as exc:
            logger.warning('v2 open failed: %s — %s', exc.code, exc.message)
            return _error(exc.code, exc.message)

    @router.post(
        '/pick-and-open',
        response_model=OpenResponse,
        summary='Pick and open an acquisition',
        description=('Display the native file picker, then open the selected acquisition and create a temporary binary-data session.'),
        responses={
            200: {'model': OpenResponse | ErrorResponse},
            415: {'model': ErrorResponse},
            422: {'model': ErrorResponse},
            500: {'model': ErrorResponse},
            504: {'model': ErrorResponse},
        },
    )
    async def pick_and_open_endpoint(
        request: PickAndOpenRequest,
    ) -> OpenResponse | JSONResponse:
        selected = await asyncio.to_thread(pick_file, request.extensions)
        if selected is None:
            return _error('cancelled', 'User cancelled file dialog', status_code=200)
        try:
            opened = await _open_threaded(
                selected,
                request.channel_indices,
                open_fn=open_fn,
            )
            return _register_opened(opened, store)
        except OpenServiceError as exc:
            logger.warning('v2 pick-and-open failed: %s — %s', exc.code, exc.message)
            return _error(exc.code, exc.message)

    @router.get(
        '/sessions/{session_id}',
        response_model=SessionResponse,
        summary='Inspect a live session',
        responses={404: {'model': ErrorResponse}},
    )
    def session_metadata(session_id: str) -> SessionResponse | JSONResponse:
        description = store.describe(session_id)
        if description is None:
            return _error(
                'session_not_found',
                f'Session not found: {session_id}',
                status_code=404,
            )
        return SessionResponse(
            session_id=description.session_id,
            ttl_seconds_remaining=description.ttl_seconds_remaining,
            channel_indices=list(description.channel_indices),
            reference_channel_indices=list(description.reference_channel_indices),
            total_bytes=description.total_bytes,
        )

    @router.delete(
        '/sessions/{session_id}',
        response_model=DeleteSessionResponse,
        summary='Delete a live session',
        responses={404: {'model': ErrorResponse}},
    )
    def delete_session(session_id: str) -> DeleteSessionResponse | JSONResponse:
        if not store.delete(session_id):
            return _error(
                'session_not_found',
                f'Session not found: {session_id}',
                status_code=404,
            )
        return DeleteSessionResponse(session_id=session_id)

    @router.get(
        '/sessions/{session_id}/channels/{channel_index}/data',
        summary='Download a source channel plane',
        description=(
            'Return one row-major little-endian float32 plane. Reshape using the shape reported by the corresponding open response.'
        ),
        responses={
            200: {
                'description': 'Raw little-endian float32 plane bytes.',
                'content': {'application/octet-stream': {'schema': {'type': 'string', 'format': 'binary'}}},
            },
            404: {'model': ErrorResponse},
            422: {'model': ErrorResponse},
        },
    )
    def channel_data(session_id: str, channel_index: int) -> Response:
        if channel_index < 0:
            return _error('channel_out_of_range', 'channelIndex must be non-negative')
        if not store.has_session(session_id):
            return _error('session_not_found', f'Session not found: {session_id}', status_code=404)
        data = store.get_channel(session_id, channel_index)
        if data is None:
            return _error(
                'channel_not_found',
                f'Channel not found: {session_id}/{channel_index}',
                status_code=404,
            )
        return Response(
            content=data,
            media_type='application/octet-stream',
            headers={'Content-Length': str(len(data)), 'Cache-Control': 'no-store'},
        )

    @router.get(
        '/sessions/{session_id}/reference/channels/{channel_index}/data',
        summary='Download a reference-image channel plane',
        description=('Return one reference-image plane in row-major little-endian float32 encoding using AcqStore coordinate semantics.'),
        responses={
            200: {
                'description': 'Raw little-endian float32 reference plane bytes.',
                'content': {'application/octet-stream': {'schema': {'type': 'string', 'format': 'binary'}}},
            },
            404: {'model': ErrorResponse},
            422: {'model': ErrorResponse},
        },
    )
    def reference_channel_data(session_id: str, channel_index: int) -> Response:
        if channel_index < 0:
            return _error('channel_out_of_range', 'channelIndex must be non-negative')
        if not store.has_session(session_id):
            return _error('session_not_found', f'Session not found: {session_id}', status_code=404)
        data = store.get_reference_channel(session_id, channel_index)
        if data is None:
            return _error(
                'reference_channel_not_found',
                f'Reference channel not found: {session_id}/{channel_index}',
                status_code=404,
            )
        return Response(
            content=data,
            media_type='application/octet-stream',
            headers={'Content-Length': str(len(data)), 'Cache-Control': 'no-store'},
        )

    return router
