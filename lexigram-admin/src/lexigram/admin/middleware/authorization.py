"""Request-entry RBAC middleware (AUTH-09, AUTH-18).

Checks every non-public request against an authorizer before dispatching
to the handler.  Returns 401 for anonymous users, 403 for authorization
denials, and is HTMX-aware.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from lexigram.admin.observability.admin_metrics import AdminMetrics
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from starlette.types import ASGIApp

logger = get_logger(__name__)

_PUBLIC_PATHS: tuple[str, ...] = (
    "/admin/login",
    "/admin/setup",
    "/admin/static",
    "/admin/health",
    "/admin/events",
)


@runtime_checkable
class RequestAuthorizerProtocol(Protocol):
    """Protocol for request-level authorization.

    Concrete implementations (e.g. PiccolinaAdminAuthPolicy) also satisfy
    ``AdminAuthorizerProtocol`` from ``lexigram-contracts`` by implementing
    the CRUD methods alongside this one.
    """

    async def authorize_request(self, user: object, request: Request) -> bool:
        """Return True if the user is authorized to access the request."""
        ...


class AdminAuthorizationMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces request-entry authorization."""

    def __init__(
        self,
        app: ASGIApp,
        authorizer: RequestAuthorizerProtocol,
        metrics: AdminMetrics | None = None,
    ) -> None:
        super().__init__(app)
        self._authorizer = authorizer
        self._metrics = metrics or AdminMetrics(None)

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Check authorization before dispatching to the next handler."""
        path = request.url.path
        if any(path.startswith(p) for p in _PUBLIC_PATHS):
            return await call_next(request)

        user = getattr(request.state, "user", None)
        if user is None:
            logger.info(
                "admin_authz.unauthenticated",
                path=path,
            )
            return self._unauthenticated(request)

        if not await self._authorizer.authorize_request(user, request):
            logger.info(
                "admin_authz.denied",
                user_id=getattr(user, "user_id", "unknown"),
                path=path,
            )
            resource = path.split("/")[2] if len(path.split("/")) > 2 else "unknown"
            self._metrics.record_authz_denied(resource=resource)
            return self._forbidden(request)

        return await call_next(request)

    @staticmethod
    def _unauthenticated(request: Request) -> JSONResponse | RedirectResponse:
        """Return 401, with JSON for HTMX requests to prevent redirect loops."""
        if request.headers.get("HX-Request") == "true":
            return JSONResponse(
                {
                    "error": "session_expired",
                    "login_url": "/admin/login",
                },
                status_code=401,
            )
        return RedirectResponse(
            url=f"/admin/login?next={request.url.path}",
            status_code=302,
        )

    @staticmethod
    def _forbidden(request: Request) -> JSONResponse:
        """Return 403 with user context."""
        return JSONResponse(
            {"error": "forbidden", "path": request.url.path},
            status_code=403,
        )


__all__ = [
    "AdminAuthorizationMiddleware",
    "RequestAuthorizerProtocol",
]
