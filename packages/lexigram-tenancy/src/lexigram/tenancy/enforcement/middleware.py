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

    This middleware **never rejects** a request; it refuses to *bind* a
    tenant it cannot verify.  It resolves the tenant, authorizes the
    binding against the caller's identity (server-verified resolvers bind
    directly; client-influenced ones require a membership cross-check),
    then sets ``TENANT_ID`` in the shared
    :class:`~lexigram.primitives.context.Context` and stores the
    :class:`~lexigram.contracts.tenancy.types.TenantInfo` in
    ``scope["state"]["tenant"]`` for downstream use by
    :class:`~lexigram.tenancy.enforcement.guard.TenantGuard`.  The context
    token is always reset on exit.

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

        Resolves the tenant, verifies it may be **bound** to the caller
        (:meth:`TenantValidator.authorize`), and sets ``TENANT_ID`` +
        ``scope["state"]["tenant"]`` only when authorization succeeds.
        The middleware never rejects the *request*; it refuses to *bind* a
        tenant it cannot verify.  The context token is always reset on
        exit.

        Args:
            scope: ASGI connection scope.
            receive: ASGI receive callable.
            send: ASGI send callable.
        """
        if scope["type"] not in ("http", "websocket"):
            await self._app(scope, receive, send)
            return

        resolution_ctx = self._build_resolution_context(scope)
        resolved = await self._resolver.resolve_with_source(resolution_ctx)

        token = None
        if resolved is not None:
            tenant_id = resolved[1]
            tenant_info = await self._validator.validate(tenant_id)
            if tenant_info:
                user_id = scope.get("state", {}).get("user_id")
                if await self._validator.authorize(
                    resolver_name=resolved[0],
                    user_id=user_id,
                    tenant_id=tenant_id,
                ):
                    token = self._ctx.set(TENANT_ID, tenant_id)
                    scope.setdefault("state", {})["tenant"] = tenant_info
                    logger.debug(
                        "tenant_context_set",
                        tenant_id=tenant_id,
                        status=str(tenant_info.status),
                    )

        try:
            await self._app(scope, receive, send)
        finally:
            if token is not None:
                self._ctx.reset(TENANT_ID, token)

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
