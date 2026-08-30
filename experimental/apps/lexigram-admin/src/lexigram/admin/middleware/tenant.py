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
        "/logout",
        "/setup",
        "/health",
        "/static",
        "/login/2fa",
        "/verify-email",
        "/password-reset",
        "/register",
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

    @staticmethod
    def _is_bypass_path(path: str) -> bool:
        """Match public paths on segment boundaries, never by raw prefix."""
        normalized = path.rstrip("/") or path
        return any(
            normalized == public or normalized.startswith(f"{public}/")
            for public in _TENANT_BYPASS_PATHS
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from starlette.datastructures import MutableHeaders
        from starlette.requests import Request
        from starlette.responses import PlainTextResponse

        request = Request(scope, receive=receive)

        from lexigram.admin.multitenancy.context import (
            reset_current_tenant,
            set_current_tenant,
        )

        # Extract path relative to admin mount
        path = request.url.path

        # Bypass for public paths
        if self._is_bypass_path(path):
            request.state.tenant_id = ""
            token = set_current_tenant("")
            try:
                await self.app(scope, receive, send)
            finally:
                reset_current_tenant(token)
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

        # Bind the resolved tenant to this async request. A ContextVar keeps
        # concurrent requests isolated while allowing data sources resolved at
        # application startup to follow the request's tenant.
        token = set_current_tenant(tenant_id)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_current_tenant(token)
