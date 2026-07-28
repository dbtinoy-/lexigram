"""Default middleware stack for Lexigram Web.

Provides :class:`DefaultMiddlewareStack` — an explicit, named class that
encapsulates the minimum set of Starlette-compatible middlewares applied by
every Lexigram web application.

Users can import this class to inspect, extend, or reproduce the default
middleware stack without relying on opaque ``WebProvider`` internals.
``WebProvider`` uses this class internally for DRY consistency.

Example::

    from lexigram.web.middleware import DefaultMiddlewareStack

    stack = DefaultMiddlewareStack(container=container)
    middlewares = stack.build()
    # pass to Starlette(middleware=middlewares, ...)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from starlette.middleware import Middleware as StarletteMiddleware
    from starlette.types import ASGIApp

    from lexigram.contracts.core.di import ContainerResolverProtocol

logger = get_logger(__name__)


class DefaultMiddlewareStack:
    """Builds the default Lexigram middleware stack as an explicit, composable list.

    Encapsulates the minimum set of middlewares that every Lexigram web
    application applies so users can see and extend it without magic.

    :class:`~lexigram.web.di.provider.WebProvider` delegates to this class
    internally, ensuring that all code paths produce the same default stack.

    Args:
        container: The resolved DI container.  Required for
            :class:`~lexigram.web.middleware.di_scope.DIScopeMiddleware` which
            provides request-scoped dependency resolution.
        extra_middlewares: Additional user-supplied Lexigram middlewares to
            include in the stack.  They are adapted to Starlette
            ``Middleware`` wrappers via
            :class:`~lexigram.web.middleware.registry.MiddlewareAdapterRegistry`
            and inserted before the built-in defaults.

    Example::

        from lexigram.web.middleware import DefaultMiddlewareStack
        from lexigram.logging import get_logger

        logger = get_logger(__name__)

        # Inspect the default stack
        stack = DefaultMiddlewareStack(container=container)
        for mw in stack.build():
            logger.debug("middleware", name=mw.cls.__name__)

        # Extend with custom middleware
        stack = DefaultMiddlewareStack(
            container=container,
            extra_middlewares=[MyTimingMiddleware()],
        )
    """

    def __init__(
        self,
        container: ContainerResolverProtocol | None = None,
        extra_middlewares: list[Any] | None = None,
    ) -> None:
        """Initialise the stack builder.

        Args:
            container: Resolved DI container for ``DIScopeMiddleware``.
            extra_middlewares: Optional extra Lexigram middlewares to include.
        """
        self._container = container
        self._extra_middlewares: list[Any] = list(extra_middlewares or [])

    def build(self) -> list[StarletteMiddleware]:
        """Build and return the ordered list of default Starlette middlewares.

        The always-present entry is
        :class:`~lexigram.web.middleware.di_scope.DIScopeMiddleware`.
        Any ``extra_middlewares`` supplied at construction time are prepended
        to that entry after adaptation.

        Returns:
            An ordered list of :class:`starlette.middleware.Middleware`
            instances ready to pass to
            :class:`starlette.applications.Starlette`.
        """
        from typing import cast

        from lexigram.web.middleware.di_scope import DIScopeMiddleware
        from lexigram.web.middleware.registry import MiddlewareAdapterRegistry

        registry = MiddlewareAdapterRegistry()

        # Start from user-supplied extras (order preserved)
        middlewares: list[Any] = list(self._extra_middlewares)

        # Always ensure DIScopeMiddleware is present for request-scoped DI
        has_scope_mw = any(isinstance(mw, DIScopeMiddleware) for mw in middlewares)
        if not has_scope_mw and self._container is not None:
            middlewares.insert(
                0,
                DIScopeMiddleware(cast("ASGIApp", None), self._container),  # type: ignore[arg-type]
            )
            logger.debug("default_middleware_stack.added_di_scope")

        adapted = [registry.adapt(mw) for mw in middlewares]
        logger.debug("default_middleware_stack.built", count=len(adapted))
        return adapted


__all__ = ["DefaultMiddlewareStack"]
