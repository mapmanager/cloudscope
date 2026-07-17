"""API v2-specific error normalization.

FastAPI normally serializes request-validation failures as a top-level
``detail`` array. API v2 instead exposes the same stable error envelope used by
its service and session errors. The custom route class is installed only on the
v2 router, so the frozen v1 contract is unaffected.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from acqstore_server.v2.schemas import ErrorDetailResponse, ErrorResponse


class StableValidationRoute(APIRoute):
    """Normalize FastAPI request-validation errors for API v2 routes only."""

    def get_route_handler(
        self,
    ) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original_handler = super().get_route_handler()

        async def stable_handler(request: Request) -> Response:
            try:
                return await original_handler(request)
            except RequestValidationError as exc:
                details = [
                    ErrorDetailResponse(
                        location=[str(part) for part in error.get('loc', ())],
                        message=str(error.get('msg', 'Invalid request value')),
                        type=str(error.get('type', 'value_error')),
                    )
                    for error in exc.errors()
                ]
                body = ErrorResponse(
                    error='request_validation_failed',
                    message='Request validation failed',
                    details=details,
                ).model_dump(by_alias=True, mode='json', exclude_none=True)
                return JSONResponse(body, status_code=422)

        return stable_handler
