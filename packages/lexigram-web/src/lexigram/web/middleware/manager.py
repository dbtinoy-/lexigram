"""Middleware manager for lexigram-web."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from starlette.middleware import Middleware as StarletteMiddleware

    from lexigram.web.di.provider import WebProvider


class WebMiddlewareManager:
    """Handles middleware adaptation and ordering for the web provider."""

    def __init__(self, provider: WebProvider):
        self.provider = provider
        from lexigram.web.middleware.registry import MiddlewareAdapterRegistry

        self.registry = MiddlewareAdapterRegistry()

    def build_native_stack(self, container: Any) -> list[StarletteMiddleware]:
        """Convert Lexigram middlewares to a native Starlette middleware stack.

        Delegates to :class:`~lexigram.web.middleware.stack.DefaultMiddlewareStack`
        so both this manager and any user code that builds a stack directly
        produce an identical result (DRY).

        Args:
            container: The resolved DI container, forwarded to
                ``DefaultMiddlewareStack`` for
                :class:`~lexigram.web.middleware.di_scope.DIScopeMiddleware`.

        Returns:
            An ordered list of :class:`starlette.middleware.Middleware`
            instances ready for :class:`starlette.applications.Starlette`.
        """
        from lexigram.web.middleware.stack import DefaultMiddlewareStack

        stack = DefaultMiddlewareStack(
            container=container,
            extra_middlewares=list(self.provider.middleware),
        )
        return stack.build()
