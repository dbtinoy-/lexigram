"""ASGI middleware that resolves the tenant and sets context."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.tenancy.types import TenantResolutionContext
from lexigram.logging import get_logger
from lexigram.primitives.context import TENANT_ID, Context

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    Scope = dict[str, Any]
    Receive = Callable[[], Awaitable[dict[str, Any]]]
    Send = Callable[[dict[str, Any]], Awaitable[None]]
    ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

logger = get_logger(__name__)


class TenantContextMiddleware:
    """ASGI middleware that resolves the tenant for every HTTP/WebSocket request.

    This middleware **never rejects** a request.  It resolves the tenant if
    possible, sets ``TENANT_ID`` in the shared :class:`~lexigram.primitives.context.Context`,
    and stores the :class:`~lexigram.contracts.tenancy.types.TenantInfo` in
    ``scope["state"]["tenant"]`` for downstream use by
    :class:`~lexigram.tenancy.enforcement.guard.TenantGuard`.

    Registration order: after ``RequestContextMiddleware`` and
    ``DIScopeMiddleware``, before application middleware.
    """

    def __init__(
        self,
        app: ASGIApp,
        resolver: Any,
        validator: Any,
        ctx: Context,
    ) -> None:
        """Initialise the middleware.

        Args:
            app: The next ASGI application in the chain.
            resolver: :class:`~lexigram.tenancy.resolution.chain.CompositeResolver`
                instance.
            validator: :class:`~lexigram.tenancy.enforcement.validator.TenantValidator`
                instance.
            ctx: The shared :class:`~lexigram.primitives.context.Context`.
        """
        self._app = app
        self._resolver = resolver
        self._validator = validator
        self._ctx = ctx

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process a single ASGI event.

        Args:
            scope: ASGI connection scope.
            receive: ASGI receive callable.
            send: ASGI send callable.
        """
        if scope["type"] not in ("http", "websocket"):
            await self._app(scope, receive, send)
            return

        resolution_ctx = self._build_resolution_context(scope)
        tenant_id = await self._resolver.resolve(resolution_ctx)

        if tenant_id:
            tenant_info = await self._validator.validate(tenant_id)
            if tenant_info:
                self._ctx.set(TENANT_ID, tenant_id)
                scope.setdefault("state", {})["tenant"] = tenant_info
                logger.debug(
                    "tenant_context_set",
                    tenant_id=tenant_id,
                    status=str(tenant_info.status),
                )

        await self._app(scope, receive, send)

    @staticmethod
    def _build_resolution_context(scope: Scope) -> TenantResolutionContext:
        """Build a :class:`~lexigram.contracts.tenancy.types.TenantResolutionContext`
        from the ASGI scope.

        Args:
            scope: ASGI connection scope.

        Returns:
            Immutable resolution context snapshot.
        """
        raw_headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
        headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in raw_headers}
        host = headers.get("host")
        path: str = scope.get("path", "")
        claims: dict[str, Any] = scope.get("state", {}).get("auth_claims", {})
        return TenantResolutionContext(
            headers=headers,
            host=host,
            path=path,
            claims=claims,
        )


__all__ = ["TenantContextMiddleware"]
