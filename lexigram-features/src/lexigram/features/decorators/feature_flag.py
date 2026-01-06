"""Async feature-flag–gated decorators.

Provides :func:`feature_flag` and :func:`require_flag` for guarding async
functions behind a named feature flag.
"""

from __future__ import annotations

from collections.abc import Callable
import functools
from typing import TYPE_CHECKING, Any, TypeVar

from lexigram.features.decorators._utils import _is_coroutinefunction, _resolve_manager
from lexigram.features.exceptions import FeatureFlagDisabledError

if TYPE_CHECKING:
    from lexigram.features.manager.flag_manager import FlagManager
    from lexigram.features.types import FlagContext

F = TypeVar("F", bound=Callable[..., Any])


def feature_flag(
    name: str,
    *,
    manager: FlagManager | None = None,
    fallback: Callable[..., Any] | None = None,
    context: FlagContext | None = None,
) -> Callable[[F], F]:
    """Decorate an async function so it only runs when *name* is enabled.

    When the flag is *disabled*:

    * If *fallback* is provided it is called with the same arguments and its
      return value is returned.
    * Otherwise :class:`~lexigram.features.exceptions.FeatureFlagDisabledError`
      is raised.

    Args:
        name: Feature flag name to check.
        manager: Explicit :class:`~lexigram.features.manager.FlagManager`; resolved
            via DI or a default when ``None``.
        fallback: Optional callable invoked when the flag is disabled.
        context: Optional evaluation context passed to the manager.

    Returns:
        A decorator for async functions.
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            mgr = _resolve_manager(manager)
            enabled = await mgr.is_enabled(name, context)
            if enabled:
                return await fn(*args, **kwargs)
            if fallback is not None:
                if _is_coroutinefunction(fallback):
                    return await fallback(*args, **kwargs)
                return fallback(*args, **kwargs)
            raise FeatureFlagDisabledError(name)

        return wrapper  # type: ignore[return-value]

    return decorator


def require_flag(
    name: str,
    *,
    manager: FlagManager | None = None,
    context: FlagContext | None = None,
) -> Callable[[F], F]:
    """Decorate an async function to raise when *name* is disabled.

    Semantically identical to :func:`feature_flag` with no fallback, but
    the intent is clearer when used as an access guard.

    Args:
        name: Feature flag name to check.
        manager: Explicit manager; resolved via DI or a default when ``None``.
        context: Optional evaluation context.

    Returns:
        A decorator for async functions.
    """
    return feature_flag(name, manager=manager, context=context)


__all__ = ["feature_flag", "require_flag"]
