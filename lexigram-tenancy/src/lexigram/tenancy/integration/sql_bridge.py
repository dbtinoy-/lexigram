"""ASGI middleware bridge: propagates core TENANT_ID to database context.

Only active when a database context supporting tenant isolation is available.
Uses DatabaseContextProtocol from contracts instead of direct lexigram-sql imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.primitives.context import TENANT_ID, Context

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    Scope = dict[str, Any]
    Receive = Callable[[], Awaitable[dict[str, Any]]]
    Send = Callable[[dict[str, Any]], Awaitable[None]]
    ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class TenantSQLContextBridge:
    """ASGI middleware that propagates the core ``TENANT_ID`` context key
    into database context for tenant-aware SQL queries.

    Uses DatabaseContextProtocol from contracts to avoid direct imports
    from lexigram-sql. Falls back gracefully when db context is unavailable.
    """

    def __init__(self, app: ASGIApp, ctx: Context) -> None:
        """Initialise the bridge.

        Args:
            app: Next ASGI application in the chain.
            ctx: Shared :class:`~lexigram.primitives.context.Context`.
        """
        self._app = app
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

        tenant_id = self._ctx.get(TENANT_ID)
        db_ctx = scope.get("state", {}).get("db_ctx")
        token = None

        if tenant_id and db_ctx:
            token = self._set_db_tenant(db_ctx, tenant_id)

        try:
            await self._app(scope, receive, send)
        finally:
            if token is not None and db_ctx is not None:
                self._reset_db_tenant(db_ctx, token)

    def _set_db_tenant(self, db_ctx: Any, tenant_id: str) -> Any | None:
        """Set tenant in database context using protocol interface."""
        try:
            set_tenant = getattr(db_ctx, "set_tenant_from_scope", None)
            if set_tenant and callable(set_tenant):
                return set_tenant({"tenant_id": tenant_id})
        except Exception:  # noqa: S110 — intentional best-effort fallback
            pass
        return None

    def _reset_db_tenant(self, db_ctx: Any, token: Any) -> None:
        """Reset tenant in database context using protocol interface."""
        try:
            reset_tenant = getattr(db_ctx, "reset_tenant", None)
            if reset_tenant and callable(reset_tenant):
                reset_tenant(token)
        except Exception:  # noqa: S110 — intentional best-effort fallback
            pass


__all__ = ["TenantSQLContextBridge"]
