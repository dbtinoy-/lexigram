"""Registry implementation for GraphQL directive handlers.

This module was split out of the package root to keep ``__init__`` focused
on exports.  ``DirectiveRegistry`` satisfies
:class:`~lexigram.contracts.graphql.DirectiveHandler`.
"""

from __future__ import annotations

from typing import Any


class DirectiveRegistry:
    """Registry-based implementation of :class:`~lexigram.contracts.graphql.DirectiveHandler`.

    Maps directive names to handler callables via :meth:`on` (decorator syntax
    or explicit :meth:`register` call).  When :meth:`apply_directive` is invoked
    with an unknown directive name, the target is returned unchanged if no
    default handler is registered, or the default handler is called.

    Args:
        default_handler: Optional fallback for unrecognised directives.
            Receives the same ``(directive_name, args, target)`` signature.
            When ``None`` (default), unknown directives are silently ignored.
    """

    def __init__(
        self,
        default_handler: Any | None = None,
    ) -> None:
        self._handlers: dict[str, Any] = {}
        self._default = default_handler

    def register(
        self,
        directive_name: str,
        handler: Any,
    ) -> None:
        """Register a handler callable for a directive.

        Args:
            directive_name: Name of the GraphQL directive (without ``@``).
            handler: Callable ``(directive_name, args, target) -> target``.
        """
        self._handlers[directive_name] = handler

    def on(self, directive_name: str) -> Any:
        """Decorator that registers a handler for *directive_name*.

        Example::

            @registry.on("auth")
            def apply_auth(name, args, target):
                target.__roles__ = args.get("roles", [])
                return target

        Args:
            directive_name: Name of the directive.

        Returns:
            Decorator that registers the decorated function.
        """

        def decorator(func: Any) -> Any:
            self.register(directive_name, func)
            return func

        return decorator

    def apply_directive(
        self,
        directive_name: str,
        args: dict[str, Any],
        target: Any,
    ) -> Any:
        """Apply a registered directive handler to *target*.

        If no handler is registered under *directive_name* the default handler
        is called if one was supplied; otherwise *target* is returned as-is.

        Args:
            directive_name: Directive to apply (without ``@``).
            args: Directive arguments from the schema.
            target: Schema element to transform.

        Returns:
            The (possibly transformed) *target*.
        """
        handler = self._handlers.get(directive_name, self._default)
        if handler is None:
            return target
        return handler(directive_name, args, target)

    def __contains__(self, directive_name: str) -> bool:
        """Return ``True`` if a handler is registered for *directive_name*."""
        return directive_name in self._handlers

    def __repr__(self) -> str:
        names = sorted(self._handlers)
        return f"DirectiveRegistry(directives={names!r})"
