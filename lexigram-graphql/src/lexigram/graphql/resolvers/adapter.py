"""Helper utilities for working with GraphQL resolvers.

This module contains the :class:`ResolverAdapter` implementation and a
convenience decorator.  They were formerly defined in the package
``__init__`` but have been moved here to keep package root clean.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.contracts.graphql import ResolverProtocol


class ResolverAdapter:
    """Adapts a plain callable to the :class:`~lexigram.contracts.graphql.ResolverProtocol` protocol.

    Accepts any sync or async callable with the signature
    ``(parent, args, context, info) -> Any`` and exposes it as a ``ResolverProtocol``
    via a ``resolve`` method.  Sync callables are called directly; their
    return value is awaited only when it happens to be a coroutine.

    Args:
        func: A sync or async callable that implements the resolver logic.
            The callable should accept up to four positional arguments:
            ``(parent, args, context, info)``.  Arguments beyond what the
            callable declares are silently dropped so that short signatures
            (e.g. ``lambda parent, args: parent.id``) work transparently.
    """

    __slots__ = ("_func", "_nparams")

    def __init__(self, func: Any) -> None:
        self._func = func
        # Introspect arity once so we can trim args at call time.
        try:
            sig = inspect.signature(func)
            self._nparams: int | None = len(sig.parameters)
        except (ValueError, TypeError):
            self._nparams = None  # unknown — pass all 4 args

    async def resolve(
        self,
        parent: Any,
        args: dict[str, Any],
        context: Any,
        info: Any,
    ) -> Any:
        """Invoke the wrapped callable with the resolver arguments.

        Args:
            parent: Parent (root) object for the field.
            args: Parsed field arguments from the GraphQL query.
            context: Shared execution context.
            info: GraphQL resolution info object.

        Returns:
            Resolved field value.
        """
        all_args = (parent, args, context, info)
        call_args = all_args[: self._nparams] if self._nparams is not None else all_args

        result = self._func(*call_args)
        if inspect.isawaitable(result):
            return await result
        return result

    def __repr__(self) -> str:
        name = getattr(self._func, "__name__", repr(self._func))
        return f"ResolverAdapter({name!r})"


def resolver(func: Any) -> ResolverAdapter:
    """Decorator that wraps a plain callable as a :class:`ResolverAdapter`.

    Example::

        @resolver
        async def user_resolver(parent, args, context, info):
            return await context.users.get(args["id"])

    Args:
        func: Callable to wrap.

    Returns:
        :class:`ResolverAdapter` wrapping *func*.
    """
    return ResolverAdapter(func)


# Type narrowing — confirm ResolverAdapter satisfies the protocol at import time.
_: ResolverProtocol = ResolverAdapter(lambda: None)
del _
