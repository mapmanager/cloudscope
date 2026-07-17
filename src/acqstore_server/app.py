"""FastAPI / NiceGUI entry for AcqStore Server."""

from __future__ import annotations

import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from acqstore_server.dialogs import pick_acquisition_file
from acqstore_server.logging_setup import ensure_logging, get_logger, log_file_path
from acqstore_server.routes import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_HOST,
    DEFAULT_PORT,
    PickFileFn,
    register_api_routes,
)
from acqstore_server.session_store import SessionStore
from acqstore_server.v2.demo import register_demo_routes as register_v2_demo_routes
from acqstore_server.v2.routes import create_router as create_v2_router
from acqstore_server.v2.session_store import SessionStore as V2SessionStore

_TRUE = {'1', 'true', 'yes', 'y', 'on'}

logger = get_logger('app')


def _env_true(name: str, default: str = '0') -> bool:
    return os.environ.get(name, default).strip().lower() in _TRUE


def create_app(
    *,
    session_store: SessionStore | None = None,
    pick_file_fn: PickFileFn | None = None,
    v2_session_store: V2SessionStore | None = None,
) -> FastAPI:
    """Build the AcqStore Server ASGI app (API-only / CLI mode).

    Args:
        session_store: Optional store override (tests).
        pick_file_fn: Optional native/open picker override (tests).
        v2_session_store: Optional API v2 store override (tests).

    Returns:
        Configured :class:`fastapi.FastAPI` instance.
    """
    ensure_logging()
    store = session_store or SessionStore()
    v2_store = v2_session_store or V2SessionStore()
    pick_file = pick_file_fn or pick_acquisition_file
    app = FastAPI(
        title='AcqStore Server',
        version=APP_VERSION,
        description=(
            'Local HTTP API for opening acquisition files with AcqStore and '
            'serving selected two-dimensional channel planes. Use /docs for '
            'interactive OpenAPI. Demo UIs at /demo/ (v1) and /demo/v2/.'
        ),
        docs_url='/docs',
        redoc_url='/redoc',
        openapi_url='/openapi.json',
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=False,
        allow_methods=['*'],
        allow_headers=['*'],
    )
    register_api_routes(app, store, pick_file, include_root_json=True, mount_demo=True)
    app.include_router(create_v2_router(store=v2_store, pick_file=pick_file))
    register_v2_demo_routes(app)
    return app


def _resolve_bind() -> tuple[str, int]:
    host = os.environ.get('ACQSTORE_SERVER_HOST', DEFAULT_HOST)
    port = int(os.environ.get('ACQSTORE_SERVER_PORT', str(DEFAULT_PORT)))
    if host not in {'127.0.0.1', 'localhost'}:
        raise SystemExit(
            f'AcqStore Server v0 binds localhost only; refused host={host!r}. '
            'Set ACQSTORE_SERVER_HOST=127.0.0.1'
        )
    return host, port


def main_uvicorn() -> None:
    """Run API-only uvicorn (no native window)."""
    import uvicorn

    ensure_logging()
    host, port = _resolve_bind()
    logger.info('%s v%s listening http://%s:%s', APP_NAME, APP_VERSION, host, port)
    logger.info('health http://%s:%s/api/v1/health', host, port)
    logger.info('demo http://%s:%s/demo/', host, port)
    logger.info('log file %s', log_file_path())
    print(f'[acqstore_server] {APP_NAME} v{APP_VERSION}')
    print(f'[acqstore_server] listening http://{host}:{port}')
    print(f'[acqstore_server] demo http://{host}:{port}/demo/')
    print(f'[acqstore_server] log {log_file_path()}')
    print('[acqstore_server] stop: Ctrl+C in this terminal')
    print(
        f'[acqstore_server] if port busy: '
        f'kill $(lsof -nP -iTCP:{port} -sTCP:LISTEN -t)'
    )

    try:
        # Use the module-level ``app`` (not factory=True) so create_app runs once.
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level='info',
        )
    except OSError as exc:
        if getattr(exc, 'errno', None) in {48, 98}:
            logger.error('Port %s already in use: %s', port, exc)
            print(
                f'[acqstore_server] ERROR: port {port} is already in use.\n'
                f'  Stop the old process, then retry:\n'
                f'    lsof -nP -iTCP:{port} -sTCP:LISTEN\n'
                f'    kill $(lsof -nP -iTCP:{port} -sTCP:LISTEN -t)\n'
                f'  See docs-dev/acqstore_server/README.md (Dev run / stop).',
                file=sys.stderr,
            )
            raise SystemExit(1) from exc
        raise


def native_ui_run_kwargs(*, host: str, port: int) -> dict[str, object]:
    """Return ``ui.run`` kwargs for the native status window.

    NiceGUI's ``ui.run`` installs Starlette ``GZipMiddleware`` by default
    (``compresslevel=9``). Browsers send ``Accept-Encoding: gzip``, and that
    middleware compresses the full body before sending response headers. Real
    float32 session planes (~20 MB) are highly compressible and take on the
    order of 15–20 seconds per GET at level 9; the same payload without gzip is
    tens of milliseconds on localhost. API-only uvicorn never installs this
    middleware. Pass ``gzip_middleware_factory=None`` so native mode matches.

    Args:
        host: Bind host for ``ui.run``.
        port: Bind port for ``ui.run``.

    Returns:
        Keyword arguments for :func:`nicegui.ui.run`.

    See also:
        https://nicegui.io/documentation/section_configuration_deployment
    """
    return {
        'host': host,
        'port': port,
        'title': 'AcqStore Server',
        'native': True,
        'reload': False,
        'dark': True,
        'window_size': (560, 640),
        'show': True,
        'storage_secret': 'acqstore-server-local',
        'fastapi_docs': True,
        'show_welcome_message': False,
        # Required: do not gzip large API session binary responses.
        'gzip_middleware_factory': None,
    }


def main_native() -> None:
    """Run NiceGUI native status window + same API routes on one port."""
    from nicegui import app as nicegui_app
    from nicegui import ui

    from acqstore_server.status_ui import build_status_page

    ensure_logging()
    host, port = _resolve_bind()
    store = SessionStore()
    v2_store = V2SessionStore()
    pick_file = pick_acquisition_file

    nicegui_app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=False,
        allow_methods=['*'],
        allow_headers=['*'],
    )
    register_api_routes(
        nicegui_app,
        store,
        pick_file,
        include_root_json=False,
        mount_demo=True,
    )
    nicegui_app.include_router(create_v2_router(store=v2_store, pick_file=pick_file))
    register_v2_demo_routes(nicegui_app)

    @ui.page('/')
    def _status_page() -> None:
        build_status_page(host=host, port=port)

    logger.info('%s v%s native UI http://%s:%s', APP_NAME, APP_VERSION, host, port)
    print(f'[acqstore_server] {APP_NAME} v{APP_VERSION} (native status UI)')
    print(f'[acqstore_server] listening http://{host}:{port}')
    print(f'[acqstore_server] demo http://{host}:{port}/demo/')
    print(f'[acqstore_server] log {log_file_path()}')
    print('[acqstore_server] Quit the status window to stop the server')

    ui.run(**native_ui_run_kwargs(host=host, port=port))


def main() -> None:
    """Entry: native status UI when ``ACQSTORE_SERVER_NATIVE=1``, else uvicorn."""
    if _env_true('ACQSTORE_SERVER_NATIVE'):
        main_native()
    else:
        main_uvicorn()


# ASGI target for ``uvicorn acqstore_server.app:app``.
app = create_app()
