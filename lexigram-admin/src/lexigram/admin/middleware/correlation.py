"""Correlation ID middleware — sets and echoes X-Request-ID."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from lexigram.admin.audit.correlation import new_correlation_id, set_correlation_id


class AdminCorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware that propagates and echoes correlation IDs.

    Reads the incoming ``X-Request-ID`` header (if present) or generates
    a new UUID hex identifier, sets it on the current contextvar, and
    echoes it back on the response.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        cid = request.headers.get("X-Request-ID") or new_correlation_id()
        set_correlation_id(cid)
        response = await call_next(request)
        response.headers["X-Request-ID"] = cid
        return response


__all__ = ["AdminCorrelationMiddleware"]
