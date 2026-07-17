"""FastAPI routes for the independent AcqStore Server API v2."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable, Sequence
from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from acqstore_server.logging_setup import get_logger
from acqstore_server.v2.encoding import encode_raw_f32_le
from acqstore_server.v2.models import OpenedAcquisition, ReferenceImageData
from acqstore_server.v2.open_service import OpenServiceError, open_acquisition
from acqstore_server.v2.schemas import (
    AxisResponse,
    ChannelResponse,
    ErrorResponse,
    OpenRequest,
    OpenResponse,
    PickAndOpenRequest,
    PlaneResponse,
    ReferenceChannelResponse,
    ReferenceResponse,
    ScanPathResponse,
    SourceResponse,
)
from acqstore_server.v2.session_store import SessionBuffers, SessionStore

PickFileFn = Callable[[Sequence[str] | None], str | None]
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
    body = ErrorResponse(error=code, message=message).model_dump(by_alias=True, mode='json')
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
                data_url=(
                    f'/api/v2/sessions/{session_id}/reference/channels/'
                    f'{channel.index}/data'
                ),
            )
            for channel in reference.channels
        ],
        line_roi=reference.line_roi,
        scan_path=scan_path,
    )


def _register_opened(opened: OpenedAcquisition, store: SessionStore) -> OpenResponse:
    channel_payloads = {
        channel.index: encode_raw_f32_le(channel.array) for channel in opened.channels
    }
    reference_payloads: dict[int, bytes] = {}
    if opened.reference is not None:
        reference_payloads = {
            channel.index: encode_raw_f32_le(channel.array)
            for channel in opened.reference.channels
        }
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


async def _open_threaded(path: str, channel_indices: Sequence[int] | None) -> OpenedAcquisition:
    timeout_s = open_load_timeout_s()
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(open_acquisition, path, channel_indices=channel_indices),
            timeout=timeout_s,
        )
    except TimeoutError as exc:
        raise OpenServiceError(
            'load_timeout',
            f'Open/decode exceeded {timeout_s:g}s for path: {path}',
        ) from exc


def create_router(*, store: SessionStore, pick_file: PickFileFn) -> APIRouter:
    """Create the API v2 router with injected session storage and file picker."""
    router = APIRouter(prefix='/api/v2', tags=['API v2'])

    @router.get('/health')
    def health() -> dict[str, object]:
        return {'ok': True, 'apiVersion': 'v2'}

    @router.post(
        '/open',
        response_model=OpenResponse,
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
            opened = await _open_threaded(request.path, request.channel_indices)
            return _register_opened(opened, store)
        except OpenServiceError as exc:
            logger.warning('v2 open failed: %s — %s', exc.code, exc.message)
            return _error(exc.code, exc.message)

    @router.post(
        '/pick-and-open',
        response_model=OpenResponse,
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
            opened = await _open_threaded(selected, request.channel_indices)
            return _register_opened(opened, store)
        except OpenServiceError as exc:
            logger.warning('v2 pick-and-open failed: %s — %s', exc.code, exc.message)
            return _error(exc.code, exc.message)

    @router.get('/sessions/{session_id}/channels/{channel_index}/data')
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

    @router.get('/sessions/{session_id}/reference/channels/{channel_index}/data')
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
