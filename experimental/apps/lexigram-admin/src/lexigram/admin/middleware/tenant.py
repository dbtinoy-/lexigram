"""Tenant resolution middleware for admin multi-tenancy support."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.admin.multitenancy.adapter import resolve_tenant_id
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

    from lexigram.admin.config import TenancyConfig

logger = get_logger(__name__)

# Public paths that bypass tenant resolution
_TENANT_BYPASS_PATHS: frozenset[str] = frozenset(
    {
        "/login",
        "/setup",
        "/health",
        "/static",
    }
)


class AdminTenantMiddleware:
    """Tenant resolution middleware.

    Resolves the current tenant ID from the request (header, cookie, or
    subdomain) and stores it in ``request.state.tenant_id``.  When tenancy
    is enabled and no tenant can be resolved for a non-public path, a
    403 response is returned.

    The middleware must be placed **before** ``AdminAuthGuardMiddleware``
    in the stack so ``request.state.tenant_id`` is available to auth and
    data layers.
    """

    def __init__(
        self,
        app: ASGIApp,
        config: TenancyConfig,
    ) -> None:
        self.app = app
        self.config = config

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from starlette.datastructures import MutableHeaders
        from starlette.requests import Request
        from starlette.responses import PlainTextResponse

        request = Request(scope, receive=receive)

        # Extract path relative to admin mount
        path = request.url.path

        # Bypass for public paths
        if any(path.startswith(p) or path == p for p in _TENANT_BYPASS_PATHS):
            request.state.tenant_id = ""
            await self.app(scope, receive, send)
            return

        # Resolve tenant ID (delegates to lexigram-tenancy when available)
        # Identity-bound resolution: when auth has already attached an
        # authenticated user with a tenant claim, it wins over client hints.
        user = getattr(request.state, "user", None)
        claim = getattr(user, "tenant_id", None) if user else None
        tenant_id = await resolve_tenant_id(
            request,
            default=self.config.default_tenant_id,
            header=self.config.header_name,
            cookie=self.config.cookie_name,
            claim=claim,
        )
        request.state.tenant_id = tenant_id

        if self.config.enabled and not tenant_id:
            logger.warning("tenant_resolution_failed", path=path)
            response = PlainTextResponse(
                "Tenant resolution failed",
                status_code=403,
            )
            await response(scope, receive, send)
            return

        # Inject tenant ID into response headers for downstream consumption
        if tenant_id:
            headers = MutableHeaders(scope=scope)
            headers.append("X-Tenant-Id", tenant_id)

        await self.app(scope, receive, send)
