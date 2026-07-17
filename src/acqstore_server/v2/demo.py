"""Static demonstration client registration for AcqStore Server API v2."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from fastapi.responses import FileResponse

from acqstore_server.logging_setup import get_logger

logger = get_logger('v2.demo')


def resolve_v2_demo_index() -> Path | None:
    """Return the packaged or source-tree API v2 demo HTML path."""
    candidates: list[Path] = []
    if getattr(sys, 'frozen', False):
        bundle_root = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
        candidates.extend(
            [
                bundle_root / 'acqstore_server' / 'static' / 'demo' / 'v2' / 'index.html',
                bundle_root / 'static' / 'demo' / 'v2' / 'index.html',
            ]
        )
    candidates.append(Path(__file__).resolve().parents[1] / 'static' / 'demo' / 'v2' / 'index.html')
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def register_demo_routes(app: Any) -> None:
    """Serve the independent API v2 JavaScript demo at ``/demo/v2/``."""

    @app.get('/demo/v2', include_in_schema=False)
    @app.get('/demo/v2/', include_in_schema=False)
    @app.get('/demo/v2/index.html', include_in_schema=False)
    def v2_demo_page() -> FileResponse:
        path = resolve_v2_demo_index()
        if path is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    'API v2 demo HTML not found in this build. Include '
                    'src/acqstore_server/static when packaging.'
                ),
            )
        return FileResponse(path, media_type='text/html; charset=utf-8')

    path = resolve_v2_demo_index()
    if path is None:
        logger.warning('API v2 demo HTML missing; /demo/v2/ will return 404')
    else:
        logger.info('API v2 demo HTML available at /demo/v2/ (%s)', path)
