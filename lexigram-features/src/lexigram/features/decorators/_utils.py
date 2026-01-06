"""Shared internal utilities for feature-flag decorators.

Not part of the public API — import from :mod:`lexigram.features.decorators`
instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from lexigram.features.manager.flag_manager import FlagManager


def _resolve_manager(manager: FlagManager | None) -> FlagManager:
    """Resolve FlagManager from provided instance, context var, or fallback.

    Resolution order:

    1. Explicit *manager* instance.
    2. Synchronous DI resolution from the ambient container.
    3. New local manager (uses ``LocalProvider`` by default).

    Args:
        manager: Explicit manager instance or ``None``.

    Returns:
        A resolved :class:`~lexigram.features.manager.FlagManager`.
    """
    if manager is not None:
        return manager

    from lexigram.di.resolution.context import current_resolver_var, get_resolver

    resolver = get_resolver(None) or current_resolver_var.get()
    if resolver is not None:
        from contextlib import suppress

        with suppress(Exception):
            if hasattr(resolver, "resolve_sync"):
                from lexigram.features.manager.flag_manager import FlagManager

                return resolver.resolve_sync(FlagManager)

    from lexigram.features.manager.flag_manager import FlagManager

    return FlagManager()


def _is_coroutinefunction(fn: Callable[..., Any]) -> bool:
    """Return True if *fn* is an async function or coroutine function.

    Args:
        fn: Any callable.

    Returns:
        True when *fn* is a coroutine function.
    """
    import asyncio
    import inspect

    return asyncio.iscoroutinefunction(fn) or inspect.iscoroutinefunction(fn)
