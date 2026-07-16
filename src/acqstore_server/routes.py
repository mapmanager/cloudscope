"""Register AcqStore Server HTTP API routes on a FastAPI app."""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from acqstore_server.logging_setup import get_logger, log_file_path
from acqstore_server.open_service import (
    OpenServiceError,
    open_path,
    parse_channel_overrides,
    parse_open_request,
    parse_pick_extensions,
)
from acqstore_server.schemas import error_body
from acqstore_server.session_store import SessionStore

APP_NAME = 'acqstore_server'
APP_VERSION = '0.1.0'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 8767

# Soft timeout for AcqImage open/decode after a path is known (not the OS picker).
DEFAULT_OPEN_LOAD_TIMEOUT_S = 120.0

_ERROR_STATUS: dict[str, int] = {
    'cancelled': 200,
    'path_not_found': 404,
    'unsupported_format': 422,
    'channel_out_of_range': 422,
    'calibration_unavailable': 422,
    'load_timeout': 504,
    'decode_failed': 500,
    'not_implemented': 501,
}


def open_load_timeout_s() -> float:
    """Return open/decode soft timeout in seconds.

    Override with env ``ACQSTORE_SERVER_OPEN_TIMEOUT_S`` (positive float).

    Returns:
        Timeout seconds used by ``/api/v1/open`` and post-pick load.
    """
    raw = os.environ.get('ACQSTORE_SERVER_OPEN_TIMEOUT_S', '').strip()
    if not raw:
        return DEFAULT_OPEN_LOAD_TIMEOUT_S
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_OPEN_LOAD_TIMEOUT_S
    if value <= 0.0:
        return DEFAULT_OPEN_LOAD_TIMEOUT_S
    return value


async def _open_path_threaded(
    path: str,
    store: SessionStore,
    *,
    calcium_channel: int,
    vessel_channel: int | None,
) -> dict[str, Any]:
    """Run :func:`open_path` off the event loop with a soft timeout.

    Args:
        path: Absolute or resolvable acquisition path.
        store: Session byte store.
        calcium_channel: Calcium channel index.
        vessel_channel: Vessel channel index, or ``None`` for single-channel.

    Returns:
        Open success payload.

    Raises:
        OpenServiceError: On domain failures or ``load_timeout``.
    """
    timeout_s = open_load_timeout_s()
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(
                open_path,
                path,
                store,
                calcium_channel=calcium_channel,
                vessel_channel=vessel_channel,
            ),
            timeout=timeout_s,
        )
    except TimeoutError as exc:
        raise OpenServiceError(
            'load_timeout',
            f'Open/decode exceeded {timeout_s:g}s for path: {path}',
        ) from exc

PickFileFn = Callable[[Sequence[str] | None], str | None]

logger = get_logger('routes')


def resolve_static_dir() -> Path | None:
    """Locate ``acqstore_server/static`` in source or frozen (PyInstaller) layouts.

    Returns:
        Directory containing ``demo/index.html``, or ``None`` if not found.
    """
    candidates: list[Path] = [Path(__file__).resolve().parent / 'static']
    if getattr(sys, 'frozen', False):
        meipass = Path(getattr(sys, '_MEIPASS', ''))
        exe_dir = Path(sys.executable).resolve().parent
        candidates.extend(
            [
                meipass / 'acqstore_server' / 'static',
                meipass / 'static',
                exe_dir / 'acqstore_server' / 'static',
                exe_dir / 'static',
            ]
        )
    for candidate in candidates:
        if (candidate / 'demo' / 'index.html').is_file():
            return candidate
    return None


def resolve_demo_index() -> Path | None:
    """Return path to ``demo/index.html`` when packaged or running from source."""
    static_dir = resolve_static_dir()
    if static_dir is None:
        return None
    return static_dir / 'demo' / 'index.html'


def register_api_routes(
    app: FastAPI,
    store: SessionStore,
    pick_file: PickFileFn,
    *,
    include_root_json: bool = True,
    mount_demo: bool = True,
) -> None:
    """Attach health/open/session/demo routes to ``app``.

    Args:
        app: FastAPI (or NiceGUI) application.
        store: Session byte store.
        pick_file: Native file picker callable.
        include_root_json: When true, register JSON ``GET /``. Disable when a
            NiceGUI status page owns ``/``.
        mount_demo: When true, serve the demo HTML under ``/demo``.
    """
    app.state.session_store = store
    app.state.pick_file_fn = pick_file

    if mount_demo:
        static_dir = resolve_static_dir()
        demo_index = resolve_demo_index()
        if static_dir is not None:
            # Useful for extra assets later; explicit FileResponse below is the
            # reliable path in NiceGUI native + PyInstaller builds.
            try:
                app.mount(
                    '/demo-assets',
                    StaticFiles(directory=str(static_dir / 'demo')),
                    name='demo_assets',
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning('Could not mount /demo-assets: %s', exc)
        else:
            logger.warning(
                'Demo static files not found (frozen=%s). Pack with --add-data for '
                'src/acqstore_server/static.',
                getattr(sys, 'frozen', False),
            )

        @app.get('/demo', include_in_schema=False)
        @app.get('/demo/', include_in_schema=False)
        @app.get('/demo/index.html', include_in_schema=False)
        def demo_page() -> FileResponse:
            path = resolve_demo_index()
            if path is None or not path.is_file():
                raise HTTPException(
                    status_code=404,
                    detail=(
                        'Demo HTML not found in this build. Rebuild with '
                        'packaging/acqstore_server/build_app.sh (includes static datas), '
                        'or run from source: uv run python -m acqstore_server'
                    ),
                )
            return FileResponse(path, media_type='text/html; charset=utf-8')

        if demo_index is not None:
            logger.info('Demo HTML available at /demo/ (%s)', demo_index)
        else:
            logger.warning('Demo HTML missing; /demo/ will 404 until static files are packed')

    if include_root_json:

        @app.get('/')
        def root() -> dict[str, Any]:
            host = os.environ.get('ACQSTORE_SERVER_HOST', DEFAULT_HOST)
            port = int(os.environ.get('ACQSTORE_SERVER_PORT', str(DEFAULT_PORT)))
            return {
                'ok': True,
                'app': APP_NAME,
                'version': APP_VERSION,
                'bind': f'{host}:{port}',
                'health': '/api/v1/health',
                'docs': '/docs',
                'redoc': '/redoc',
                'openapi': '/openapi.json',
                'demo': '/demo/',
                'logFile': str(log_file_path()),
                'hint': (
                    'Interactive API docs: /docs . Demo UI: /demo/ . '
                    'Clients: POST /api/v1/pick-and-open or /api/v1/open.'
                ),
            }

    @app.get('/api/v1/health')
    def health() -> dict[str, Any]:
        host = os.environ.get('ACQSTORE_SERVER_HOST', DEFAULT_HOST)
        port = int(os.environ.get('ACQSTORE_SERVER_PORT', str(DEFAULT_PORT)))
        return {
            'ok': True,
            'app': APP_NAME,
            'version': APP_VERSION,
            'bind': f'{host}:{port}',
            'docs': '/docs',
            'demo': '/demo/',
            'logFile': str(log_file_path()),
        }

    @app.post('/api/v1/open')
    async def open_endpoint(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            body = None
        try:
            if not isinstance(body, dict):
                raise OpenServiceError('path_not_found', 'JSON body object required')
            path, calcium_ch, vessel_ch = parse_open_request(body)
            payload = await _open_path_threaded(
                path,
                store,
                calcium_channel=calcium_ch,
                vessel_channel=vessel_ch,
            )
            return JSONResponse(payload)
        except OpenServiceError as exc:
            logger.warning('open failed: %s — %s', exc.code, exc.message)
            status = _ERROR_STATUS.get(exc.code, 500)
            return JSONResponse(error_body(exc.code, exc.message), status_code=status)

    @app.post('/api/v1/pick-and-open')
    async def pick_and_open_endpoint(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            body = {}
        if body is None:
            body = {}
        try:
            if not isinstance(body, dict):
                raise OpenServiceError('unsupported_format', 'JSON body object required')
            calcium_ch, vessel_ch = parse_channel_overrides(body)
            extensions = parse_pick_extensions(body)
            logger.info('pick-and-open dialog requested')
            selected = await asyncio.to_thread(pick_file, extensions)
            if selected is None:
                logger.info('pick-and-open cancelled')
                return JSONResponse(
                    error_body('cancelled', 'User cancelled file dialog'),
                    status_code=200,
                )
            logger.info('pick-and-open selected path=%s', selected)
            payload = await _open_path_threaded(
                selected,
                store,
                calcium_channel=calcium_ch,
                vessel_channel=vessel_ch,
            )
            return JSONResponse(payload)
        except OpenServiceError as exc:
            logger.warning('pick-and-open failed: %s — %s', exc.code, exc.message)
            status = _ERROR_STATUS.get(exc.code, 500)
            return JSONResponse(error_body(exc.code, exc.message), status_code=status)

    @app.get('/api/v1/session/{session_id}/channel/{role}')
    def channel_bytes(session_id: str, role: str) -> Response:
        if role not in {'calcium', 'vessels'}:
            return JSONResponse(
                error_body('channel_out_of_range', f'Unknown role: {role}'),
                status_code=422,
            )
        data = store.get_channel(session_id, role)
        if data is None:
            return JSONResponse(
                error_body('path_not_found', f'Session/channel not found: {session_id}/{role}'),
                status_code=404,
            )
        return Response(
            content=data,
            media_type='application/octet-stream',
            headers={
                'Content-Length': str(len(data)),
                'Cache-Control': 'no-store',
            },
        )

    @app.get('/api/v1/session/{session_id}/reference/channel/{channel}')
    def reference_channel(session_id: str, channel: int) -> Response:
        if channel < 0:
            return JSONResponse(
                error_body('channel_out_of_range', f'channel must be >= 0, got {channel}'),
                status_code=422,
            )
        data = store.get_reference(session_id, channel)
        if data is None:
            return JSONResponse(
                error_body(
                    'path_not_found',
                    f'Reference channel not found: {session_id}/{channel}',
                ),
                status_code=404,
            )
        return Response(
            content=data,
            media_type='application/octet-stream',
            headers={
                'Content-Length': str(len(data)),
                'Cache-Control': 'no-store',
            },
        )
